import random

from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def define(the_string):
    return the_string


@register.simple_tag
def env(key):
    return getattr(settings, key)


@register.simple_tag
def logo(logo_type):
    return static(f"img/{settings.PROJECT_NAME_UPPER}_{logo_type}.png")


@register.simple_tag
def media_url():
    return settings.MEDIA_URL


@register.simple_tag
def static_url():
    return settings.STATIC_URL


@register.filter
def divide(value, arg):
    try:
        return int(value) / int(arg)
    except (ValueError, ZeroDivisionError):
        return None


@register.filter
def random_number(value):
    """
    Returns a random number between 0 and 20 for animation delays.
    Usage: {{ value|random_number }}
    """
    return random.uniform(0, 20)


@register.filter
def multiply(value, arg):
    """
    Multiplies the value by the argument.
    Usage: {{ value|multiply:2 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.simple_tag(takes_context=True)
def get_current_template(context):
    """
    Returns the current template name from the template context
    """
    if hasattr(context, "template") and hasattr(context.template, "name"):
        return context.template.name
    return None
