from bleach.css_sanitizer import CSSSanitizer
from django.conf import settings


def get_bleach_default_options():
    bleach_args = {}
    bleach_settings = {
        "BLEACH_ALLOWED_TAGS": "tags",
        "BLEACH_ALLOWED_ATTRIBUTES": "attributes",
        "BLEACH_ALLOWED_STYLES": "css_sanitizer",
        "BLEACH_STRIP_TAGS": "strip",
        "BLEACH_STRIP_COMMENTS": "strip_comments",
        "BLEACH_ALLOWED_PROTOCOLS": "protocols",
    }

    for setting, kwarg in bleach_settings.items():
        if hasattr(settings, setting):
            attr = getattr(settings, setting)
            if setting == "BLEACH_ALLOWED_STYLES":
                attr = CSSSanitizer(allowed_css_properties=attr)
            bleach_args[kwarg] = attr

    return bleach_args
