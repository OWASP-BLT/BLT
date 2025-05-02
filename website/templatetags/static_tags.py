from django import template
from django.contrib.staticfiles.storage import staticfiles_storage

register = template.Library()

@register.simple_tag
def static_safe(path, default_path=None):
    """
    Get the URL of a static file like {% static %} but with a fallback path option.
    If the file doesn't exist, returns the URL of the default path if provided,
    otherwise returns an empty string.
    """
    try:
        return staticfiles_storage.url(path)
    except ValueError:
        if default_path:
            try:
                return staticfiles_storage.url(default_path)
            except ValueError:
                pass
        return ""