import ipaddress

from django.core.cache import cache
from django.http import HttpResponseForbidden
from user_agents import parse

from website.models import IP, Blocked


class IPRestrictMiddleware:
    """
    Middleware to restrict access based on client IP addresses and user agents.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def blocked_ips(self):
        """
        Retrieve blocked IP addresses from cache or database.
        """
        blocked_ips = cache.get("blocked_ips")
        if blocked_ips is None:
            blocked_addresses = Blocked.objects.values_list("address", flat=True)
            blocked_ips = set(filter(None, blocked_addresses))
            cache.set("blocked_ips", blocked_ips, timeout=86400)
        return blocked_ips

    def ip_in_ips(self, ip, blocked_ips):
        if blocked_ips is None:
            return False
        return ip in blocked_ips

    def blocked_ip_network(self):
        """
        Retrieve blocked IP networks from cache or database.
        """
        blocked_ip_network = cache.get("blocked_ip_network")
        if blocked_ip_network is None:
            blocked_network = Blocked.objects.values_list("ip_network", flat=True)
            blocked_ip_network = [
                ipaddress.ip_network(range_str, strict=False)
                for range_str in filter(None, blocked_network)
            ]
            cache.set("blocked_ip_network", blocked_ip_network, timeout=86400)
        return blocked_ip_network or []

    def ip_in_range(self, ip, blocked_ip_network):
        """
        Check if the IP address is within any of the blocked IP networks.
        """
        if not blocked_ip_network:
            return False
        ip_obj = ipaddress.ip_address(ip)
        return any(ip_obj in ip_range for ip_range in blocked_ip_network if ip_range)

    def blocked_agents(self):
        """
        Retrieve blocked user agents from cache or database.
        """
        blocked_agents = cache.get("blocked_agents")
        if blocked_agents is None or blocked_agents == []:
            blocked_user_agents = Blocked.objects.values_list("user_agent_string", flat=True)
            if blocked_user_agents:
                blocked_agents = set(blocked_user_agents)
                cache.set("blocked_agents", blocked_agents, timeout=86400)
                return blocked_agents
            else:
                return None
        return blocked_agents

    def is_user_agent_blocked(self, user_agent, blocked_agents):
        """
        Check if the user agent is in the list of blocked user agents.
        """
        user_agent_str = str(user_agent).strip()

        if not blocked_agents:
            return False
        blocked_agents = [str(agent).strip() for agent in blocked_agents if str(agent).strip()]

        for blocked_agent in blocked_agents:
            blocked_agent_str = str(blocked_agent).strip()
            if blocked_agent_str.lower() in user_agent_str.lower():
                return True

        return False

    def delete_all_info(self):
        Blocked.objects.all().delete()
        cache.delete("blocked_ips")
        cache.delete("blocked_ip_network")
        cache.delete("blocked_agents")

    def __call__(self, request):
        """
        Process the request and restrict access based on IP address and user agent.
        """
        ip = request.META.get("REMOTE_ADDR")
        agent = request.META.get("HTTP_USER_AGENT", "")
        #user_agent = parse(agent)
        # If you want to clear everything use this
        # self.delete_all_info()

        if (
            self.ip_in_ips(ip, self.blocked_ips())
            or self.ip_in_range(ip, self.blocked_ip_network())
            or self.is_user_agent_blocked(agent, self.blocked_agents())
        ):
            if self.ip_in_ips(ip, self.blocked_ips()) or self.ip_in_range(
                ip, self.blocked_ip_network()
            ):
                return HttpResponseForbidden(
                    "Your IP address is restricted from accessing this site."
                )
            if self.is_user_agent_blocked(agent, self.blocked_agents()):
                return HttpResponseForbidden(
                    "Your user agent is restricted from accessing this site."
                )

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")

        if ip:
            ip_record, created = IP.objects.get_or_create(
                address=ip, defaults={"agent": agent, "count": 1, "path": request.path}
            )
            if not created:
                ip_record.agent = agent
                ip_record.count += 1
                ip_record.path = request.path
                ip_record.save()

        return self.get_response(request)
