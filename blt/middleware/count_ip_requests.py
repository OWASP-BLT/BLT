from django.utils.deprecation import MiddlewareMixin
from user_agents import parse

from website.models import IP


class MonitorIPMiddleware(MiddlewareMixin):
    def process_request(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")

        user_agent = request.META.get("HTTP_USER_AGENT", "")
        parsed_agent = parse(user_agent)

        if ip:
            # Retrieve the IP object or None if it doesn't exist
            ip_record = IP.objects.filter(address=ip).first()

            if ip_record:
                # Update the count and save
                ip_record.user_agent_string = parsed_agent
                ip_record.count += 1
                ip_record.save()
                print(f"Updated IP record with address {ip}. New count: {ip_record.count}")
            else:
                print(f"IP {ip} does not exist in the database.")
