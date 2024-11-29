from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Return the value for `key` in `dictionary`."""
    return dictionary.get(key)
