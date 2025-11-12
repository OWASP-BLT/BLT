# sizzle/context_processors.py
from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loader import get_template


def sizzle_context(request):
    """Provide sizzle-specific template context for seamless integration"""

    # Check if the project has a sidenav template (for BLT integration)
    try:
        get_template("includes/sidenav.html")
        has_sidenav = True
    except TemplateDoesNotExist:
        has_sidenav = False

    # Get the base template to extend from project settings or use default
    parent_base = getattr(settings, "SIZZLE_PARENT_BASE", None)

    return {
        "sizzle_has_sidenav": has_sidenav,
        "parent_base": parent_base,  # This allows templates to extend the right base
    }
