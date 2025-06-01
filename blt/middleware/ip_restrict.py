import ipaddress
import logging

from django.core.cache import cache
from django.db import models, transaction
from django.db.utils import OperationalError
from django.http import HttpResponseForbidden

from website.models import IP, Blocked

MAX_COUNT = 2147483647
CACHE_TIMEOUT = 86400  # 24 hours
logger = logging.getLogger(__name__)


class IPRestrictMiddleware:
    """
    Middleware to restrict access based on client IP addresses and user agents.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def get_cached_data(self, cache_key, queryset_func, timeout=CACHE_TIMEOUT):
        """
        Retrieve data from cache or database with error handling.
        """
        try:
            cached_data = cache.get(cache_key)
            if cached_data is None:
                cached_data = list(filter(None, queryset_func()))
                cache.set(cache_key, cached_data, timeout=timeout)
            return cached_data
        except Exception as e:
            logger.error(f"Error in get_cached_data for {cache_key}: {str(e)}")
            return []

    def blocked_ips(self):
        """
        Retrieve blocked IP addresses from cache or database.
        """

        def get_ips():
            return Blocked.objects.values_list("address", flat=True)

        return set(self.get_cached_data("blocked_ips", get_ips))

    def blocked_ip_network(self):
        """
        Retrieve blocked IP networks from cache or database.
        """

        def get_networks():
            return Blocked.objects.values_list("ip_network", flat=True)

        blocked_ip_network = []
        for range_str in self.get_cached_data("blocked_ip_network", get_networks):
            try:
                network = ipaddress.ip_network(range_str, strict=False)
                blocked_ip_network.append(network)
            except ValueError:
                logger.warning(f"Invalid IP network format: {range_str}")
                continue
        return blocked_ip_network

    def blocked_agents(self):
        """
        Retrieve blocked user agents from cache or database.
        """

        def get_agents():
            return Blocked.objects.values_list("user_agent_string", flat=True)

        return set(self.get_cached_data("blocked_agents", get_agents))

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
            return any(ip_obj in ip_range for ip_range in blocked_ip_network)
        except ValueError:
            logger.warning(f"Invalid IP address format: {ip}")
            return False

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
        Increment the block count for a specific IP, network, or user agent.
        """
        try:
            with transaction.atomic():
                if ip:
                    blocked_entry = Blocked.objects.select_for_update().filter(address=ip).first()
                elif network:
                    blocked_entry = Blocked.objects.select_for_update().filter(ip_network=network).first()
                elif user_agent:
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
                    return

                if blocked_entry:
                    blocked_entry.count = models.F("count") + 1
                    blocked_entry.save(update_fields=["count"])
        except OperationalError as e:
            logger.error(f"Database error while incrementing block count: {str(e)}")
        except Exception as e:
            logger.error(f"Error incrementing block count: {str(e)}")

    def __call__(self, request):
        try:
            ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
                "REMOTE_ADDR", ""
            )
            agent = request.META.get("HTTP_USER_AGENT", "").strip()

            # Get all blocked data from cache first
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

            if self.is_user_agent_blocked(agent, blocked_agents):
                self.increment_block_count(user_agent=agent)
                return HttpResponseForbidden()

            if ip:
                try:
                    with transaction.atomic():
                        ip_records = IP.objects.select_for_update().filter(address=ip, path=request.path)
                        if ip_records.exists():
                            ip_record = ip_records.first()
                            new_count = min(ip_record.count + 1, MAX_COUNT)
                            ip_record.agent = agent
                            ip_record.count = new_count
                            if ip_record.pk:
                                ip_record.save(update_fields=["agent", "count"])
                            if not transaction.get_autocommit():
                                ip_records.exclude(pk=ip_record.pk).delete()
                        else:
                            IP.objects.create(address=ip, agent=agent, count=1, path=request.path)
                except OperationalError as e:
                    logger.error(f"Database error while updating IP record: {str(e)}")
                except Exception as e:
                    logger.error(f"Error updating IP record: {str(e)}")

            return self.get_response(request)
        except Exception as e:
            logger.error(f"Error in IPRestrictMiddleware: {str(e)}")
            return self.get_response(request)
