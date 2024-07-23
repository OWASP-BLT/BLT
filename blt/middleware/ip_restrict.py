import os

from django.http import HttpResponseForbidden


class IPRestrictMiddleware:
    """
    Middleware to restrict access based on client IP addresses.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.ip_file_path = "website/restricted_ip.txt"

    def _load_restricted_ips(self):
        if not os.path.exists(self.ip_file_path):
            return []

        with open(self.ip_file_path, "r") as file:
            return [line.strip() for line in file]

    def __call__(self, request):
        ip = request.META.get("REMOTE_ADDR")
        restricted_ips = self._load_restricted_ips()

        if ip in restricted_ips:
            return HttpResponseForbidden("Your IP address is restricted from accessing this site.")

        response = self.get_response(request)
        return response
