import ipaddress

from django.core.cache import cache
from django.db import models, transaction
from django.http import HttpResponseForbidden

from website.models import IP, Blocked

MAX_COUNT = 2147483647

CACHE_TIMEOUT = 86400  # 1 day, adjust as needed


class IPRestrictMiddleware:
    """
    Middleware to restrict access based on client IP addresses and user agents.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    # ----------------------------------------------------------------------
    #                     Caching and Data Retrieval
    # ----------------------------------------------------------------------

    def get_blocked_entries(self):
        """
        Retrieve all blocked entries from cache or database. We store the
        entire list of Blocked objects (or a subset of fields) in cache once.
        """
        blocked_data = cache.get("blocked_entries")
        if blocked_data is None:
            # You can store only the fields needed if you prefer:
            # e.g., list(Blocked.objects.values('pk', 'address', 'ip_network', 'user_agent_string', 'count'))
            blocked_data = list(Blocked.objects.all())
            cache.set("blocked_entries", blocked_data, CACHE_TIMEOUT)
        return blocked_data

    def get_blocked_ips(self):
        """
        Build a set of blocked IP addresses from the cached blocked entries.
        """
        ips = cache.get("blocked_ips")
        if ips is None:
            entries = self.get_blocked_entries()
            # Filter out empty or None addresses, convert to a set
            ips = {entry.address for entry in entries if entry.address}
            cache.set("blocked_ips", ips, CACHE_TIMEOUT)
        return ips

    def get_blocked_networks(self):
        """
        Build a list of blocked IP networks (ipaddress.ip_network objects)
        from the cached blocked entries.
        """
        networks = cache.get("blocked_networks")
        if networks is None:
            entries = self.get_blocked_entries()
            networks = []
            for entry in entries:
                if entry.ip_network:
                    try:
                        net = ipaddress.ip_network(entry.ip_network, strict=False)
                        networks.append(net)
                    except ValueError:
                        # Skip invalid networks
                        pass
            cache.set("blocked_networks", networks, CACHE_TIMEOUT)
        return networks

    def get_blocked_agents(self):
        """
        Build a set of blocked user-agent substrings (lowercase) from the
        cached blocked entries.
        """
        agents = cache.get("blocked_agents")
        if agents is None:
            entries = self.get_blocked_entries()
            # Filter out empty or None user_agent_string, convert to lowercase set
            agents = {
                entry.user_agent_string.lower() for entry in entries if entry.user_agent_string
            }
            cache.set("blocked_agents", agents, CACHE_TIMEOUT)
        return agents

    # ----------------------------------------------------------------------
    #                        Core Utility Methods
    # ----------------------------------------------------------------------

    def get_client_ip(self, request):
        """
        Extract the client IP address from the request.
        """
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def get_user_agent(self, request):
        """
        Extract the user agent string from the request.
        """
        return request.META.get("HTTP_USER_AGENT", "").strip()

    def ip_in_ips(self, ip, blocked_ips):
        """
        Check if the IP address is in the set of blocked IPs.
        """
        return ip in blocked_ips

    def ip_in_networks(self, ip, blocked_networks):
        """
        Check if the IP address is within any of the blocked IP networks.
        Returns the matching network if found, else None.
        """
        if not ip:
            return None
        ip_obj = ipaddress.ip_address(ip)
        for net in blocked_networks:
            if ip_obj in net:
                return net
        return None

    def is_user_agent_blocked(self, user_agent, blocked_agents):
        """
        Check if the user agent matches any of the blocked user agent
        substrings (case-insensitive).
        """
        ua_lower = user_agent.lower()
        return any(blocked_ua in ua_lower for blocked_ua in blocked_agents)

    # ----------------------------------------------------------------------
    #                Incrementing the Block Count in the DB
    # ----------------------------------------------------------------------

    def increment_block_count(self, ip=None, network=None, user_agent=None):
        """
        Increment the block count for the matching Blocked entry.
        Since the actual update must happen in the DB, we do one minimal query:
        we find the relevant entry by IP, or by network, or by user_agent substring.
        """
        if not (ip or network or user_agent):
            return  # Nothing to increment

        with transaction.atomic():
            # We'll do a single lookup based on what's provided.
            # Searching by IP / network is straightforward. Searching by user_agent
            # (substring) requires an __icontains lookup or a manual filter.
            qs = Blocked.objects.select_for_update()

            if ip:
                qs = qs.filter(address=ip)
            elif network:
                qs = qs.filter(ip_network=network)
            elif user_agent:
                # If multiple user_agent_strings can match, you might want to refine logic here.
                qs = qs.filter(user_agent_string__iexact=user_agent) | qs.filter(
                    user_agent_string__icontains=user_agent
                )

            blocked_entry = qs.first()
            if blocked_entry:
                blocked_entry.count = models.F("count") + 1
                blocked_entry.save(update_fields=["count"])

    # ----------------------------------------------------------------------
    #                 Recording General IP Usage in IP Model
    # ----------------------------------------------------------------------

    def record_ip_usage(self, ip, agent, path):
        """
        Create or update the IP record for (ip, path) with an incremented count.
        """
        with transaction.atomic():
            ip_record_qs = IP.objects.select_for_update().filter(address=ip, path=path)
            if ip_record_qs.exists():
                ip_record = ip_record_qs.first()
                ip_record.agent = agent
                ip_record.count = min(ip_record.count + 1, MAX_COUNT)
                ip_record.save(update_fields=["agent", "count"])

                # Clean up any other records with the same (ip, path) but different PKs
                ip_record_qs.exclude(pk=ip_record.pk).delete()
            else:
                IP.objects.create(address=ip, agent=agent, count=1, path=path)

    # ----------------------------------------------------------------------
    #                           Main Handler
    # ----------------------------------------------------------------------

    def __call__(self, request):
        ip = self.get_client_ip(request)
        agent = self.get_user_agent(request)

        # Grab cached block sets/lists (1 DB call if cache is empty)
        blocked_ips = self.get_blocked_ips()
        blocked_networks = self.get_blocked_networks()
        blocked_agents = self.get_blocked_agents()

        # 1) Check if IP is explicitly blocked
        if ip and self.ip_in_ips(ip, blocked_ips):
            self.increment_block_count(ip=ip)
            return HttpResponseForbidden()

        # 2) Check if IP is in any blocked network
        network_hit = self.ip_in_networks(ip, blocked_networks)
        if network_hit:
            self.increment_block_count(network=str(network_hit))
            return HttpResponseForbidden()

        # 3) Check if user agent is blocked
        if agent and self.is_user_agent_blocked(agent, blocked_agents):
            self.increment_block_count(user_agent=agent)
            return HttpResponseForbidden()

        # 4) Record IP usage if present
        if ip:
            self.record_ip_usage(ip, agent, request.path)

        return self.get_response(request)
