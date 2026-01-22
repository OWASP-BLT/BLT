import ipaddress
import logging

# IP restriction middleware for BLT
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
from django.db.transaction import TransactionManagementError
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
                continue

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
        """
        Check if the IP address is in the list of blocked IPs.
        """
        return ip in blocked_ips

    def ip_in_range(self, ip, blocked_ip_network):
        """
        Check if the IP address is within any of the blocked IP networks.
        """
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
        """
        Asynchronous version of increment_block_count
        """
        await sync_to_async(self.increment_block_count)(ip, network, user_agent)

    def increment_block_count(self, ip=None, network=None, user_agent=None):
        """
        Increment the block count for a specific IP, network, or user agent in the Blocked model.
        """
        try:
            with transaction.atomic():
                # Check if we're in a broken transaction
                if transaction.get_rollback():
                    logger.warning("Skipping block count increment - transaction marked for rollback")
                    return

                # Use atomic QuerySet.update() with F() instead of save()
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
        """
        Asynchronous version of IP record creation/update logic
        """
        if not ip:
            return

        await sync_to_async(self._record_ip)(ip, agent, path)

    def _record_ip(self, ip, agent, path):
        """
        Helper method to record IP information
        """
        # Skip IP recording during tests to avoid transaction management issues
        if getattr(settings, "IS_TEST", False) or getattr(settings, "TESTING", False):
            return

        try:
            with transaction.atomic():
                # Check if we're in a broken transaction
                if transaction.get_rollback():
                    logger.warning(f"Skipping IP recording for {ip} - transaction marked for rollback")
                    return

                # Try to update existing record using atomic QuerySet.update() with F()
                updated = IP.objects.filter(address=ip, path=path).update(
                    agent=agent,
                    count=models.Case(
                        models.When(count__lt=MAX_COUNT, then=models.F("count") + 1),
                        default=models.Value(MAX_COUNT),
                        output_field=models.BigIntegerField(),
                    ),
                )

                # If no record was updated, create a new one
                if updated == 0:
                    IP.objects.create(address=ip, agent=agent, count=1, path=path)

                # Clean up any duplicate records (should be rare)
                # Use a separate query to avoid issues with the atomic block
                duplicates = IP.objects.filter(address=ip, path=path).order_by("created")[1:]
                if duplicates.exists():
                    duplicate_ids = list(duplicates.values_list("id", flat=True))
                    IP.objects.filter(id__in=duplicate_ids).delete()

        except TransactionManagementError as e:
            # Handle transaction management errors during IP recording.
            # Log with full context so that real issues are visible in production logs.
            logger.warning(
                "Transaction management error while recording IP %s: %s",
                ip,
                e,
                exc_info=True,
            )
        except Exception as e:
            # Log the error but don't let it break the request
            logger.error(f"Error recording IP {ip}: {str(e)}", exc_info=True)

    def __call__(self, request):
        return self.process_request_sync(request)

    async def __acall__(self, request):
        """
        Asynchronous version of the middleware call method
        """
        # Get client information
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
        agent = request.META.get("HTTP_USER_AGENT", "").strip()

        # Check cache for blocked items
        blocked_ips = await sync_to_async(self.blocked_ips)()
        blocked_ip_network = await sync_to_async(self.blocked_ip_network)()
        blocked_agents = await sync_to_async(self.blocked_agents)()

        # Check if IP is blocked directly
        if await sync_to_async(self.ip_in_ips)(ip, blocked_ips):
            await self.increment_block_count_async(ip=ip)
            return HttpResponseForbidden()

        # Check if IP is in a blocked network
        if await sync_to_async(self.ip_in_range)(ip, blocked_ip_network):
            # Find the specific network that caused the block and increment its count
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

        # Record IP information
        await self.record_ip_async(ip, agent, request.path)

        # Continue with the request
        response = await self.get_response(request)
        return response

    def process_request_sync(self, request):
        """
        Synchronous version of the middleware logic
        """
        # Get client information
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
        agent = request.META.get("HTTP_USER_AGENT", "").strip()

        # Check cache for blocked items
        blocked_ips = self.blocked_ips()
        blocked_ip_network = self.blocked_ip_network()
        blocked_agents = self.blocked_agents()

        # Check if IP is blocked directly
        if self.ip_in_ips(ip, blocked_ips):
            self.increment_block_count(ip=ip)
            return HttpResponseForbidden()

        # Check if IP is in a blocked network
        if self.ip_in_range(ip, blocked_ip_network):
            # Find the specific network that caused the block and increment its count
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

        # Record IP information
        if ip:
            self._record_ip(ip, agent, request.path)

        # Continue with the request
        return self.get_response(request)
