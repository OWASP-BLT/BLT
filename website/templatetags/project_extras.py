from django import template

register = template.Library()


@register.filter
def sum_attr(queryset, attr_name):
    """Sum an attribute value of all objects in a queryset"""
    total = 0
    for obj in queryset:
        value = getattr(obj, attr_name, None)
        if value is not None:
            total += value
    return total
