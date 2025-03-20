from django import template

register = template.Library()


@register.filter
def divide(value, arg):
    """Divides the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0


@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except ValueError:
        return 0


@register.filter
def subtract(value, arg):
    """Subtracts the argument from the value"""
    try:
        return float(value) - float(arg)
    except ValueError:
        return 0


@register.filter
def add(value, arg):
    """Adds the argument to the value"""
    try:
        return float(value) + float(arg)
    except ValueError:
        return 0


@register.filter
def percentage(value, arg):
    """Returns the percentage of value to arg"""
    try:
        return float(value) / float(arg) * 100
    except (ValueError, ZeroDivisionError):
        return 0


@register.filter
def divisibleby(value, arg):
    """Returns whether the value is divisible by the argument"""
    try:
        return float(value) % float(arg) == 0
    except (ValueError, ZeroDivisionError):
        return False
