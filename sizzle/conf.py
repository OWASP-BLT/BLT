from django.conf import settings

SIZZLE_SETTINGS = {
    'BASE_TEMPLATE': getattr(settings, 'SIZZLE_BASE_TEMPLATE', 'base.html'),
    'USE_PROJECT_BASE': getattr(settings, 'SIZZLE_USE_PROJECT_BASE', False),
}