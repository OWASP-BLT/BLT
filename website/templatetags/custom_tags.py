from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def define(the_string):
    return the_string

@register.simple_tag
def env(key):
    return getattr(settings,key)

@register.simple_tag
def logo(logo_type):    
    return static(F"img/{settings.PROJECT_NAME_UPPER}_{logo_type}.png")