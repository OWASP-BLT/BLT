import ipaddress
import logging
import sys

from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.db import models, transaction
from django.http import HttpResponseForbidden

from website.models import IP, Blocked

MAX_COUNT = 2147483647

logger = logging.getLogger(__name__)


class IPRestrictMiddleware:
    """
    Middleware to restrict access based on client IP addresses and user agent.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def get_cached_data(self, cache_key, queryset, timeout=86400):
        cached_data = cache.get(cache_key)
        if cached_data is None:
            cached_data = list(filter(None, queryset))
            cache.set(cache_key, cached_data, timeout=timeout)
        return cached_data

    def blocked_ips(self):
        """
        Retrieve blocked IP addresses from cache or database.
        """
        blocked_addresses = Blocked.objects.filter(address__isnull=False).values_list("address", flat=True)
        return set(self.get_cached_data("blocked_ips", blocked_addresses))

    def blocked_ip_network(self):
        """
        Retrieve blocked IP networks from cache or database.
        """
        blocked_network = Blocked.objects.filter(ip_network__isnull=False).values_list("ip_network", flat=True)
        blocked_ip_network = []

        for range_str in self.get_cached_data("blocked_ip_network", blocked_network):
            try:
                network = ipaddress.ip_network(range_str, strict=False)
                blocked_ip_network.append(network)
            except ValueError as e:
                logger.error(f"Invalid IP network {range_str}: {str(e)}")

        return blocked_ip_network

    def blocked_agents(self):
        """
        Retrieve blocked user agents from cache or database.
        """
        blocked_user_agents = Blocked.objects.filter(user_agent_string__isnull=False).values_list(
            "user_agent_string", flat=True
        )
        return set(self.get_cached_data("blocked_agents", blocked_user_agents))

    def ip_in_ips(self, ip, blocked_ips):
        return ip in blocked_ips

    def ip_in_range(self, ip, blocked_ip_network):
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError as e:
            logger.error(f"Invalid IP address {ip}: {str(e)}")
            return False

        return any(ip_obj in ip_range for ip_range in blocked_ip_network)

    def is_user_agent_blocked(self, user_agent, blocked_agents):
        """
        Check if the user agent is in the list of blocked user agents by checking if the
        full user agent string contains any of the blocked substrings.
        Returns the matching blocked pattern if found, None otherwise.
        """
        if not user_agent or not blocked_agents:
            return None

        user_agent_str = str(user_agent).strip().lower()
        for blocked_agent in blocked_agents:
            if blocked_agent.lower() in user_agent_str:
                return blocked_agent  # Return the specific matching pattern
        return None

    async def increment_block_count_async(self, ip=None, network=None, user_agent=None):
        await sync_to_async(self.increment_block_count)(ip, network, user_agent)

    def increment_block_count(self, ip=None, network=None, user_agent=None):
        try:
            with transaction.atomic(savepoint=True):
                if transaction.get_rollback():
                    return

                if ip:
                    Blocked.objects.filter(address=ip).update(count=models.F("count") + 1)
                elif network:
                    Blocked.objects.filter(ip_network=network).update(count=models.F("count") + 1)
                elif user_agent:
                    # user_agent is now the specific blocked pattern, not the full incoming string
                    Blocked.objects.filter(user_agent_string=user_agent).update(count=models.F("count") + 1)
        except Exception as e:
            logger.error(f"Error incrementing block count: {str(e)}", exc_info=True)

    async def record_ip_async(self, ip, agent, path):
        if not ip:
            return
        await sync_to_async(self._record_ip)(ip, agent, path)

    def _record_ip(self, ip, agent, path):
        """
        Record IP safely.
        Must never break requests or tests.
        """

        if "test" in sys.argv:
            return

        try:
            with transaction.atomic(savepoint=True):
                if transaction.get_rollback():
                    return

                updated = IP.objects.filter(address=ip, path=path).update(
                    agent=agent,
                    count=models.Case(
                        models.When(count__lt=MAX_COUNT, then=models.F("count") + 1),
                        default=models.Value(MAX_COUNT),
                        output_field=models.BigIntegerField(),
                    ),
                )

                if updated == 0:
                    IP.objects.create(address=ip, agent=agent, count=1, path=path)

                duplicates = IP.objects.filter(address=ip, path=path).order_by("created")[1:]
                if duplicates.exists():
                    IP.objects.filter(id__in=duplicates.values_list("id", flat=True)).delete()

        except Exception:
            logger.debug(f"IP logging skipped for {ip}", exc_info=True)

    def __call__(self, request):
        return self.process_request_sync(request)

    async def __acall__(self, request):
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
        agent = request.META.get("HTTP_USER_AGENT", "").strip()

        blocked_ips = await sync_to_async(self.blocked_ips)()
        blocked_ip_network = await sync_to_async(self.blocked_ip_network)()
        blocked_agents = await sync_to_async(self.blocked_agents)()

        if await sync_to_async(self.ip_in_ips)(ip, blocked_ips):
            await self.increment_block_count_async(ip=ip)
            return HttpResponseForbidden()

        if await sync_to_async(self.ip_in_range)(ip, blocked_ip_network):
            for network in blocked_ip_network:
                if ipaddress.ip_address(ip) in network:
                    await self.increment_block_count_async(network=str(network))
                    break
            return HttpResponseForbidden()

        # Check if user agent is blocked
        matching_pattern = await sync_to_async(self.is_user_agent_blocked)(agent, blocked_agents)
        if matching_pattern:
            await self.increment_block_count_async(user_agent=matching_pattern)
            return HttpResponseForbidden()

        await self.record_ip_async(ip, agent, request.path)
        response = await self.get_response(request)
        return response

    def process_request_sync(self, request):
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
        agent = request.META.get("HTTP_USER_AGENT", "").strip()

        blocked_ips = self.blocked_ips()
        blocked_ip_network = self.blocked_ip_network()
        blocked_agents = self.blocked_agents()

        if self.ip_in_ips(ip, blocked_ips):
            self.increment_block_count(ip=ip)
            return HttpResponseForbidden()

        if self.ip_in_range(ip, blocked_ip_network):
            for network in blocked_ip_network:
                if ipaddress.ip_address(ip) in network:
                    self.increment_block_count(network=str(network))
                    break
            return HttpResponseForbidden()

        # Check if user agent is blocked
        matching_pattern = self.is_user_agent_blocked(agent, blocked_agents)
        if matching_pattern:
            self.increment_block_count(user_agent=matching_pattern)
            return HttpResponseForbidden()

        if ip:
            self._record_ip(ip, agent, request.path)

        return self.get_response(request)
