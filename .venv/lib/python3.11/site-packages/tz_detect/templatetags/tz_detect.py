from django import template
from django.conf import settings

from ..utils import convert_header_name

register = template.Library()


@register.inclusion_tag("tz_detect/detector.html", takes_context=True)
def tz_detect(context, **script_attrs):
    return {
        "show": not hasattr(context.get("request"), "timezone_active"),
        "debug": getattr(settings, "DEBUG", False),
        "csrf_header_name": convert_header_name(getattr(settings, "CSRF_HEADER_NAME", "HTTP_X_CSRFTOKEN")),
        "script_attrs": script_attrs,
    }
