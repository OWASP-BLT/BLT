# sizzle/context_processors.py
from django.template.loader import get_template
from django.template import TemplateDoesNotExist

def sizzle_context(request):
    try:
        get_template('includes/sidenav.html')
        has_sidenav = True
    except TemplateDoesNotExist:
        has_sidenav = False
    
    return {
        'sizzle_has_sidenav': has_sidenav
    }