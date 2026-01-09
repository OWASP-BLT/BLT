from datetime import datetime
from itertools import chain

import pytz

from .defaults import TZ_DETECT_COUNTRIES


def get_prioritized_timezones():
    def tz_gen():
        for c in TZ_DETECT_COUNTRIES:
            yield pytz.country_timezones(c)
        yield pytz.common_timezones

    return chain.from_iterable(tz_gen())


def offset_to_timezone(offset, now=None):
    """Convert a minutes offset (JavaScript-style) into a pytz timezone

    The ``now`` parameter is generally used for testing only
    """
    now = now or datetime.now()

    # JS offsets are flipped, so unflip.
    user_offset = -offset

    # Helper: timezone offset in minutes
    def get_tz_offset(tz):
        try:
            return tz.utcoffset(now).total_seconds() / 60
        except (pytz.NonExistentTimeError, pytz.AmbiguousTimeError):
            return tz.localize(now, is_dst=False).utcoffset().total_seconds() / 60

    # Return the timezone with the minimum difference to the user's offset.
    return min(
        (pytz.timezone(tz_name) for tz_name in get_prioritized_timezones()),
        key=lambda tz: abs(get_tz_offset(tz) - user_offset),
    )


def convert_header_name(django_header):
    """Converts header name from django settings to real header name.

    For example:
    'HTTP_CUSTOM_CSRF' -> 'custom-csrf'
    """
    return django_header.lower().replace("_", "-").split("http-")[-1]
