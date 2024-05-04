# Python2 does not have FileNotFoundError
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

from django.conf import settings
from django import template
import humanize


register = template.Library()


def init():
    """ Initialize the lib

    Function-design use is to be able to test language settings changes
    """

    if settings.USE_L10N:
        locale = settings.LANGUAGE_CODE.replace('-', '_')
        try:
            humanize.i18n.activate(locale)
        except FileNotFoundError:
            pass  # Just let it to the default locale

    HUMANIZE_FUNC_LIST = [
        'naturalday',
        'naturaltime',
        'ordinal',
        'intword',
        'naturaldelta',
        'intcomma',
        'apnumber',
        'fractional',
        'naturalsize',
        'naturaldate'
    ]

    # registers all humanize functions as template tags
    for funcname in HUMANIZE_FUNC_LIST:
        func = getattr(humanize, funcname)
        register.filter(funcname, func, is_safe=True)

init()
