import ipaddress

from django.core.cache import cache
from django.db import models, transaction
from django.http import HttpResponseForbidden

from website.models import IP, Blocked

MAX_COUNT = 2147483647  # Maximum value for the count field


class IPRestrictMiddleware:
    """
    Middleware to restrict access based on client IP addresses and user agents.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def get_cached_data(self, cache_key, queryset, timeout=86400):
        """
        Retrieve data from cache or database.
        """
        cached_data = cache.get(cache_key)
        if cached_data is None:
            cached_data = list(filter(None, queryset))  # Filter out None values
            cache.set(cache_key, cached_data, timeout=timeout)
        return cached_data

    def blocked_ips(self):
        """
        Retrieve blocked IP addresses from cache or database.
        """
        blocked_addresses = Blocked.objects.values_list("address", flat=True)
        return set(self.get_cached_data("blocked_ips", blocked_addresses))

    def blocked_ip_network(self):
        """
        Retrieve blocked IP networks from cache or database.
        """
        blocked_network = Blocked.objects.values_list("ip_network", flat=True)
        blocked_ip_network = []

        for range_str in self.get_cached_data("blocked_ip_network", blocked_network):
            try:
                network = ipaddress.ip_network(range_str, strict=False)
                blocked_ip_network.append(network)
            except ValueError:
                # Skip invalid networks
                continue

        return blocked_ip_network

    def blocked_agents(self):
        """
        Retrieve blocked user agents from cache or database.
        """
        blocked_user_agents = Blocked.objects.values_list("user_agent_string", flat=True)
        # Filter out None values
        blocked_user_agents = [agent for agent in blocked_user_agents if agent is not None]
        return set(self.get_cached_data("blocked_agents", blocked_user_agents))

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
        Check if the user agent is in the list of blocked user agents.
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
        if ip:
            blocked_entry = Blocked.objects.select_for_update().filter(address=ip).first()
        elif network:
            blocked_entry = Blocked.objects.select_for_update().filter(ip_network=network).first()
        elif user_agent:
            # Find if any user_agent_string is a substring of the user_agent
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

    def _update_or_create_ip_record(self, ip, agent, path):
        """
        Helper method to update or create an IP record.
        """
        ip_records = IP.objects.select_for_update().filter(address=ip, path=path)
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

            # Delete duplicate records
            ip_records.exclude(pk=ip_record.pk).delete()
        else:
            # If no record exists, create a new one
            IP.objects.create(address=ip, agent=agent, count=1, path=path)

    def __call__(self, request):
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
        agent = request.META.get("HTTP_USER_AGENT", "").strip()

        blocked_ips = self.blocked_ips()
        blocked_ip_network = self.blocked_ip_network()
        blocked_agents = self.blocked_agents()

        # Check if the IP, network, or user agent is blocked
        if self.ip_in_ips(ip, blocked_ips):
            transaction.on_commit(lambda: self.increment_block_count(ip=ip))
            return HttpResponseForbidden()

        if self.ip_in_range(ip, blocked_ip_network):
            for network in blocked_ip_network:
                if ipaddress.ip_address(ip) in network:
                    transaction.on_commit(lambda: self.increment_block_count(network=str(network)))
                    break
            return HttpResponseForbidden()

        if self.is_user_agent_blocked(agent, blocked_agents):
            transaction.on_commit(lambda: self.increment_block_count(user_agent=agent))
            return HttpResponseForbidden()

        # Update or create IP record (deferred until after the main transaction commits)
        if ip:
            transaction.on_commit(lambda: self._update_or_create_ip_record(ip, agent, request.path))

        return self.get_response(request)
