# avoid using custom filters if possible
import json

import bleach
import markdown
from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()

# Allowed tags and attributes for sanitizing markdown HTML
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li', 'blockquote',
    'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'table',
    'thead', 'tbody', 'tr', 'th', 'td', 'img', 'div', 'span'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'code': ['class'],
    'div': ['class'],
    'span': ['class'],
    'th': ['align'],
    'td': ['align'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


@register.filter
def get_item(dictionary, key):
    """Return the value for `key` in `dictionary`."""
    return dictionary.get(key)


@register.filter
def before_dot(value):
    return str(value).split(".")[0]


@register.filter(name="to_json", is_safe=True)
def to_json(value):
    """Convert Python object to JSON string"""
    return mark_safe(json.dumps(value, cls=DjangoJSONEncoder))


@register.filter
@stringfilter
def markdown_filter(value):
    """Converts markdown text to HTML with XSS protection."""
    # Convert markdown to HTML
    html = markdown.markdown(value, extensions=["extra", "nl2br", "sane_lists"])
    
    # Sanitize HTML to prevent XSS
    sanitized = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True
    )
    
    return mark_safe(sanitized)
