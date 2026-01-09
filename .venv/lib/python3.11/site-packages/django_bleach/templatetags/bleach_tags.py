import bleach
from django import template
from django.utils.safestring import mark_safe

from django_bleach.utils import get_bleach_default_options

register = template.Library()


@register.filter(name="bleach")
def bleach_value(value, tags=None):
    if value is None:
        return None

    bleach_args = get_bleach_default_options()
    if tags is not None:
        args = bleach_args.copy()
        args["tags"] = tags.split(",")
    else:
        args = bleach_args
    bleached_value = bleach.clean(value, **args)
    return mark_safe(bleached_value)


@register.filter
def bleach_linkify(value):
    """
    Convert URL-like strings in an HTML fragment to links

    This function converts strings that look like URLs, domain names and email
    addresses in text that may be an HTML fragment to links, while preserving:

        1. links already in the string
        2. urls found in attributes
        3. email addresses
    """
    if value is None:
        return None

    return bleach.linkify(value, parse_email=True)
