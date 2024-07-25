from django.http import HttpResponseForbidden

from website.models import BlockedIP


class IPRestrictMiddleware:
    """
    Middleware to restrict access based on client IP addresses.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def blocked_ips(self, request):
        # Retrieve all blocked IP addresses from the database
        blocked_addresses = BlockedIP.objects.values_list("address", flat=True)
        return set(blocked_addresses)  # Use a set for faster lookup

    def __call__(self, request):
        ip = request.META.get("REMOTE_ADDR")

        if ip:
            blocked_ips = self.blocked_ips(request)
            if ip in blocked_ips:
                return HttpResponseForbidden(
                    "Your IP address is restricted from accessing this site."
                )

        response = self.get_response(request)
        return response
