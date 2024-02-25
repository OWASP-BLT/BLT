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
