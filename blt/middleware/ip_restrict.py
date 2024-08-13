import ipaddress

from django.core.cache import cache
from django.db import models, transaction
from django.http import HttpResponseForbidden

from website.models import IP, Blocked


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
            cached_data = list(filter(None, queryset))
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
        blocked_ip_network = [
            ipaddress.ip_network(range_str, strict=False)
            for range_str in self.get_cached_data("blocked_ip_network", blocked_network)
        ]
        return blocked_ip_network

    def blocked_agents(self):
        """
        Retrieve blocked user agents from cache or database.
        """
        blocked_user_agents = Blocked.objects.values_list("user_agent_string", flat=True)
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
        user_agent_str = str(user_agent).strip().lower()
        return any(blocked_agent.lower() in user_agent_str for blocked_agent in blocked_agents)

    def __call__(self, request):
        """
        Process the request and restrict access based on IP address and user agent.
        """
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
            "REMOTE_ADDR", ""
        )
        agent = request.META.get("HTTP_USER_AGENT", "").strip()

        blocked_ips = self.blocked_ips()
        blocked_ip_network = self.blocked_ip_network()
        blocked_agents = self.blocked_agents()

        if (
            self.ip_in_ips(ip, blocked_ips)
            or self.ip_in_range(ip, blocked_ip_network)
            or self.is_user_agent_blocked(agent, blocked_agents)
        ):
            return HttpResponseForbidden()

        if ip:
            with transaction.atomic():
                ip_records = IP.objects.select_for_update().filter(address=ip)
                if ip_records.exists():
                    # Aggregate the count and delete duplicates
                    count_sum = sum(record.count for record in ip_records)
                    ip_record = ip_records.first()
                    ip_record.agent = agent
                    ip_record.count = models.F("count") + count_sum
                    ip_record.path = request.path
                    ip_record.save(update_fields=["agent", "count", "path"])

                    # Delete all but the first record
                    ip_records.exclude(pk=ip_record.pk).delete()
                else:
                    # If no record exists, create a new one
                    IP.objects.create(address=ip, agent=agent, count=1, path=request.path)

        return self.get_response(request)
