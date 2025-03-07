import ipaddress

from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.db import models, transaction
from django.http import HttpResponseForbidden

from website.models import IP, Blocked

MAX_COUNT = 2147483647


class IPRestrictMiddleware:
    """
    Middleware to restrict access based on client IP addresses and user agents.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Initialize cache on startup to avoid DB hits on first requests
        self.initialize_cache()

    def initialize_cache(self):
        """Initialize cache keys on startup to avoid DB hits on first requests"""
        # Preload blocked data into cache
        try:
            self._get_blocked_ips()
            self._get_blocked_ip_networks()
            self._get_blocked_agents()
        except Exception:
            # Fail silently during initialization - we'll try again on first request
            pass

    def get_cached_data(self, cache_key, queryset, timeout=86400):
        """
        Retrieve data from cache or database.
        """
        cached_data = cache.get(cache_key)
        if cached_data is None:
            cached_data = list(filter(None, queryset))  # Filter out None values
            cache.set(cache_key, cached_data, timeout=timeout)
        return cached_data

    def _get_blocked_ips(self):
        """Helper method for retrieving blocked IPs"""
        blocked_addresses = Blocked.objects.values_list("address", flat=True)
        return [addr for addr in blocked_addresses if addr is not None]

    def _get_blocked_ip_networks(self):
        """Helper method for retrieving blocked IP networks"""
        blocked_network = Blocked.objects.values_list("ip_network", flat=True)
        return [network for network in blocked_network if network is not None]

    def _get_blocked_agents(self):
        """Helper method for retrieving blocked user agents"""
        user_agents = Blocked.objects.values_list("user_agent_string", flat=True)
        return [agent for agent in user_agents if agent is not None]

    def blocked_ips(self):
        """
        Retrieve blocked IP addresses from cache or database.
        """
        cached_ips = cache.get("blocked_ips")
        if cached_ips is None:
            cached_ips = set(self.get_cached_data("blocked_ips", self._get_blocked_ips()))
            cache.set("blocked_ips", cached_ips, timeout=86400)
        return cached_ips

    def blocked_ip_network(self):
        """
        Retrieve blocked IP networks from cache or database.
        """
        cached_networks = cache.get("blocked_ip_network")
        if cached_networks is not None:
            return cached_networks

        blocked_network = self._get_blocked_ip_networks()
        blocked_ip_network = []

        for range_str in self.get_cached_data("blocked_ip_network", blocked_network):
            try:
                network = ipaddress.ip_network(range_str, strict=False)
                blocked_ip_network.append(network)
            except ValueError:
                # Log the error or handle it as needed, but skip invalid networks
                continue

        cache.set("blocked_ip_network", blocked_ip_network, timeout=86400)
        return blocked_ip_network

    def blocked_agents(self):
        """
        Retrieve blocked user agents from cache or database.
        """
        cached_agents = cache.get("blocked_agents")
        if cached_agents is None:
            blocked_user_agents = self._get_blocked_agents()
            cached_agents = set(self.get_cached_data("blocked_agents", blocked_user_agents))
            cache.set("blocked_agents", cached_agents, timeout=86400)
        return cached_agents

    def ip_in_ips(self, ip, blocked_ips):
        """
        Check if the IP address is in the list of blocked IPs.
        """
        return ip in blocked_ips

    def ip_in_range(self, ip, blocked_ip_network):
        """
        Check if the IP address is within any of the blocked IP networks.
        """
        ip_obj = ipaddress.ip_address(ip)
        return any(ip_obj in ip_range for ip_range in blocked_ip_network)

    def is_user_agent_blocked(self, user_agent, blocked_agents):
        """
        Check if the user agent is in the list of blocked user agents by checking if the
        full user agent string contains any of the blocked substrings.
        """
        if not user_agent or not blocked_agents:
            return False

        user_agent_str = str(user_agent).strip().lower()
        return any(
            blocked_agent.lower() in user_agent_str for blocked_agent in blocked_agents if blocked_agent is not None
        )

    def increment_block_count(self, ip=None, network=None, user_agent=None):
        """
        Increment the block count for a specific IP, network, or user agent in the Blocked model.
        """
        with transaction.atomic():
            if ip:
                blocked_entry = Blocked.objects.select_for_update().filter(address=ip).first()
            elif network:
                blocked_entry = Blocked.objects.select_for_update().filter(ip_network=network).first()
            elif user_agent:
                # Correct lookup: find if any user_agent_string is a substring of the user_agent
                blocked_entry = (
                    Blocked.objects.select_for_update()
                    .filter(
                        user_agent_string__in=[
                            agent
                            for agent in Blocked.objects.values_list("user_agent_string", flat=True)
                            if agent is not None and user_agent is not None and agent.lower() in user_agent.lower()
                        ]
                    )
                    .first()
                )
            else:
                return  # Nothing to increment

            if blocked_entry:
                blocked_entry.count = models.F("count") + 1
                blocked_entry.save(update_fields=["count"])

    async def increment_block_count_async(self, ip=None, network=None, user_agent=None):
        """
        Asynchronous version of increment_block_count that can be called from an async context.
        """
        await sync_to_async(self.increment_block_count)(ip=ip, network=network, user_agent=user_agent)

    async def __call__(self, request):
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
        agent = request.META.get("HTTP_USER_AGENT", "").strip()

        # Get blocked information from cache
        blocked_ips = self.blocked_ips()
        blocked_ip_network = self.blocked_ip_network()
        blocked_agents = self.blocked_agents()

        # Check if request should be blocked
        if self.ip_in_ips(ip, blocked_ips):
            await self.increment_block_count_async(ip=ip)
            return HttpResponseForbidden()

        if self.ip_in_range(ip, blocked_ip_network):
            # Find the specific network that caused the block and increment its count
            for network in blocked_ip_network:
                if ipaddress.ip_address(ip) in network:
                    await self.increment_block_count_async(network=str(network))
                    break
            return HttpResponseForbidden()

        if self.is_user_agent_blocked(agent, blocked_agents):
            await self.increment_block_count_async(user_agent=agent)
            return HttpResponseForbidden()

        # Record IP information
        if ip:

            def record_ip():
                with transaction.atomic():
                    # create unique entry for every unique (ip,path) tuple
                    # if this tuple already exists, we just increment the count.
                    ip_records = IP.objects.select_for_update().filter(address=ip, path=request.path)
                    if ip_records.exists():
                        ip_record = ip_records.first()

                        # Calculate the new count and ensure it doesn't exceed the MAX_COUNT
                        new_count = ip_record.count + 1
                        if new_count > MAX_COUNT:
                            new_count = MAX_COUNT

                        ip_record.agent = agent
                        ip_record.count = new_count
                        if ip_record.pk:
                            ip_record.save(update_fields=["agent", "count"])

                        # Check if a transaction is already active before starting a new one
                        if not transaction.get_autocommit():
                            ip_records.exclude(pk=ip_record.pk).delete()
                    else:
                        # If no record exists, create a new one
                        IP.objects.create(address=ip, agent=agent, count=1, path=request.path)

            # We don't await this since we don't need to wait for it to complete
            # to return the response
            try:
                await sync_to_async(record_ip)()
            except Exception:
                # If recording IP fails, we still want to proceed with the request
                pass

        return await self.get_response(request)
