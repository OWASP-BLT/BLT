from django.utils.deprecation import MiddlewareMixin
from user_agents import parse

from website.models import MonitorIP


class MonitorIPMiddleware(MiddlewareMixin):
    def process_request(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
            print(x_forwarded_for)
        else:
            ip = request.META.get("REMOTE_ADDR")
        # ip = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        parsed_agent = parse(user_agent)
        print(parsed_agent)

        if ip:
            obj, created = MonitorIP.objects.get_or_create(
                ip=ip, user_agent=parsed_agent, defaults={"count": 1}
            )

            if not created:
                # Existing IP record, increment the count
                obj.count += 1
                obj.save()
