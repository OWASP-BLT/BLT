import ipaddress

from django.core.cache import cache
from django.http import HttpResponseForbidden
from user_agents import parse

from website.models import BlockedIP


class IPRestrictMiddleware:
    """
    Middleware to restrict access based on client IP addresses.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def blocked_ips(self):
        blocked_ips = cache.get("blocked_ips")
        if blocked_ips is None:
            blocked_addresses = BlockedIP.objects.values_list("address", flat=True)
            blocked_ips = set(blocked_addresses)
            cache.set("blocked_ips", blocked_ips, timeout=86400)
        return blocked_ips

    def blocked_ip_ranges(self):
        blocked_ip_ranges = cache.get("blocked_ip_ranges")
        if blocked_ip_ranges is None:
            blocked_ip_start = BlockedIP.objects.values_list("address_range_start", flat=True)
            blocked_ip_end = BlockedIP.objects.values_list("address_range_end", flat=True)
            blocked_ip_ranges = list(zip(blocked_ip_start, blocked_ip_end))
            cache.set("blocked_ip_ranges", blocked_ip_ranges, timeout=86400)
        return blocked_ip_ranges

    def ip_in_range(self, ip, ip_ranges):
        ip_int = int(ipaddress.IPv4Address(ip))
        for start, end in ip_ranges:
            start_int = int(ipaddress.IPv4Address(start))
            end_int = int(ipaddress.IPv4Address(end))
            if start_int <= ip_int <= end_int:
                return True
        return False

    def blocked_agents(self):
        blocked_agents = cache.get("blocked_agents")
        if blocked_agents is None:
            blocked_user_agents = BlockedIP.objects.values_list("user_agent_string", flat=True)
            blocked_agents = set(blocked_user_agents)
            cache.set("blocked_agents", blocked_agents, timeout=86400)
        return blocked_agents

    def __call__(self, request):
        ip = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        parsed_agent = parse(user_agent)

        if ip:
            if ip in self.blocked_ips():
                return HttpResponseForbidden(
                    "Your IP address is restricted from accessing this site."
                )
            blocked_ip_ranges = self.blocked_ip_ranges()
            if self.ip_in_range(ip, blocked_ip_ranges):
                return HttpResponseForbidden(
                    "Your IP address is restricted from accessing this site."
                )
        if parsed_agent and parsed_agent in self.blocked_agents():
            return HttpResponseForbidden("Your IP address is restricted from accessing this site.")

        return self.get_response(request)
