from django.utils.deprecation import MiddlewareMixin

from .models import IP


class LogRequestMiddleware(MiddlewareMixin):
    def process_request(self, request):
        ip_address = request.META.get("REMOTE_ADDR")
        request_path = request.path
        IP.objects.create(
            address=ip_address,
            path=request_path,
        )
