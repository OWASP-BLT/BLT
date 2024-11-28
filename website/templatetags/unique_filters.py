from django import template

register = template.Library()


@register.filter
def unique(value, arg):
    """Returns unique objects based on a property"""
    if not value:
        return []

    try:
        seen = set()
        unique_list = []
        for obj in value:
            val = getattr(obj, arg, None)
            if val is not None and val not in seen:
                seen.add(val)
                unique_list.append(obj)
        return unique_list
    except (AttributeError, TypeError):
        return value  # Return original value if there's an error
