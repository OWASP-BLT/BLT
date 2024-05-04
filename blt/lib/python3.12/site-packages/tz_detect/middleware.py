import pytz
from django.utils import timezone
from pytz.tzinfo import BaseTzInfo

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:  # Django < 1.10
    MiddlewareMixin = object

from .utils import offset_to_timezone


class TimezoneMiddleware(MiddlewareMixin):
    def process_request(self, request):
        tz = request.session.get("detected_tz")
        if tz:
            # ``request.timezone_active`` is used in the template tag
            # to detect if the timezone has been activated
            request.timezone_active = True
            # for existing sessions storing BaseTzInfo objects
            if isinstance(tz, BaseTzInfo):
                timezone.activate(tz)
            elif isinstance(tz, str):
                timezone.activate(pytz.timezone(tz))
            else:
                timezone.activate(offset_to_timezone(tz))
        else:
            timezone.deactivate()
