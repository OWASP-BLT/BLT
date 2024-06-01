from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from ..helpers import GRAVATAR_DEFAULT_SIZE, get_gravatar_profile_url, get_gravatar_url

# Get template.Library instance
register = template.Library()


def gravatar_url(user_or_email, size=GRAVATAR_DEFAULT_SIZE):
    """ Builds a gravatar url from an user or email """
    if hasattr(user_or_email, 'email'):
        email = user_or_email.email
    else:
        email = user_or_email

    try:
        return escape(get_gravatar_url(email=email, size=size))
    except:
        return ''


def gravatar(user_or_email, size=GRAVATAR_DEFAULT_SIZE, alt_text='', css_class='gravatar'):
    """ Builds an gravatar <img> tag from an user or email """
    if hasattr(user_or_email, 'email'):
        email = user_or_email.email
    else:
        email = user_or_email

    try:
        url = escape(get_gravatar_url(email=email, size=size))
    except:
        return ''

    return mark_safe(
        '<img class="{css_class}" src="{src}" width="{width}"'
        ' height="{height}" alt="{alt}" />'.format(
            css_class=css_class, src=url, width=size, height=size, alt=alt_text
        )
    )


def gravatar_profile_url(user_or_email):
    if hasattr(user_or_email, 'email'):
        email = user_or_email.email
    else:
        email = user_or_email

    try:
        return escape(get_gravatar_profile_url(email))
    except:
        return ''

register.simple_tag(gravatar_url)
register.simple_tag(gravatar)
register.simple_tag(gravatar_profile_url)
