import json
import random
from datetime import timedelta

from django import template
from django.conf import settings
from django.db import models
from django.templatetags.static import static
from django.utils import timezone

from website.models import IP, DailyStats

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
def get_current_url_path(context):
    """
    Returns the current URL path from the request
    """
    request = context.get("request")
    if request:
        return request.path
    return None


@register.simple_tag(takes_context=True)
def get_current_template(context):
    """
    Returns the current template name from the template context
    """

    if hasattr(context, "template") and hasattr(context.template, "name"):
        return context.template.name
    return None


@register.simple_tag
def get_page_views(url_path, days=30):
    """
    Returns page view data for the last N days for a specific URL path,
    as a JSON dictionary with dates as keys and view counts as values.
    """
    # Get the date range
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Query the IP table for views of this page
    daily_views = (
        IP.objects.filter(path__contains=url_path, created__gte=start_date, created__lte=end_date)
        .values("created__date")
        .annotate(total_views=models.Sum("count"))
        .order_by("created__date")
    )

    # Create a dictionary with dates as keys and view counts as values
    view_counts_dict = {}

    # First, initialize the dictionary with zeros for all dates in the range
    for i in range(days):
        current_date = (start_date + timedelta(days=i)).date()
        formatted_date = current_date.strftime("%Y-%m-%d")
        view_counts_dict[formatted_date] = 0

    # Then populate with actual view data where available
    for entry in daily_views:
        try:
            date_str = entry["created__date"].strftime("%Y-%m-%d")
            # Ensure view count is an integer
            count = int(entry["total_views"])
            view_counts_dict[date_str] = count
        except (AttributeError, ValueError, TypeError) as e:
            # In case of any error, just skip this entry but don't crash
            continue

    # Return as JSON string
    return json.dumps(view_counts_dict)


@register.simple_tag
def get_page_votes(template_name, vote_type="upvote"):
    """
    Returns the vote count for a specific template
    """
    # Clean the template name to use as a key
    page_key = template_name.replace("/", "_").replace(".html", "")

    # Create the vote key
    vote_key = f"{vote_type}_{page_key}"

    # Try to get the vote count from DailyStats
    try:
        stat = DailyStats.objects.get(name=vote_key)
        return int(stat.value)
    except (DailyStats.DoesNotExist, ValueError):
        return 0


@register.filter
def timestamp_to_datetime(timestamp):
    """
    Convert a Unix timestamp to a datetime object.

    Args:
        timestamp (int): Unix timestamp in seconds

    Returns:
        datetime: Datetime object
    """
    try:
        # Convert to integer first to handle string inputs
        timestamp_int = int(float(timestamp))
        return timezone.datetime.fromtimestamp(timestamp_int)
    except (ValueError, TypeError):
        return None


@register.filter
def div(value, arg):
    """
    Divide the value by the argument.

    Args:
        value (float): The numerator
        arg (float): The denominator

    Returns:
        float: The result of the division
    """
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0


@register.filter
def cut(value, arg):
    """
    Removes all instances of arg from the given string.

    Args:
        value (str): The string to modify
        arg (str): The substring to remove

    Returns:
        str: The modified string with all instances of arg removed
    """
    try:
        return str(value).replace(arg, "")
    except (ValueError, TypeError):
        return value

@register.filter
def format_security_timedelta(td):
    """Convert a timedelta object into a human-readable string."""
    if not td:
        return "N/A"
    total_seconds = int(td.total_seconds())
    days = total_seconds // (24 * 3600)  # Calculate days first
    hours = (total_seconds % (24 * 3600)) // 3600  # Get remaining hours after days
    minutes = (total_seconds % 3600) // 60  # Get remaining minutes
    return f"{days} days, {hours} hours, {minutes} minutes"