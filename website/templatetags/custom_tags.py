from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def define(the_string):
    return the_string

@register.simple_tag
def env(key):
    return getattr(settings,key)
