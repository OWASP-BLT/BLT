from django import template

register = template.Library()


@register.filter
def split(value, arg):
    """Split a string by the given separator."""
    if value:
        return value.split(arg)
    return []
