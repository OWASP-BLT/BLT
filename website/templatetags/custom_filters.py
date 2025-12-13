# avoid using custom filters if possible
import json

from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Return the value for `key` in `dictionary`."""
    return dictionary.get(key)


@register.filter
def before_dot(value):
    return str(value).split(".")[0]


@register.filter(name="to_json", is_safe=True)
def to_json(value):
    """Convert Python object to JSON string"""
    return mark_safe(json.dumps(value, cls=DjangoJSONEncoder))


@register.filter
def replace(value, arg):
    """Replace substring. Usage: {{ value|replace:"old|new" }}"""
    if arg is None:
        return value
    old_new = str(arg).split("|", 1)
    if len(old_new) == 2:
        old, new = old_new
        return str(value).replace(old, new)
    return value
