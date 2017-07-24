"""
Django settings for gettingstarted project, on Heroku. For more info, see:
https://github.com/heroku/heroku-django-template

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

import os
import sys

import dj_database_url
from django.http import Http404
from django.utils.translation import ugettext_lazy as _

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ADMIN_URL = os.environ.get('ADMIN_URL', 'admin')
DEFAULT_FROM_EMAIL = "support@bugheist.com"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: change this before deploying to production!
SECRET_KEY = 'i+acxn5(akgsn!sr4^qgf(^m&*@+g1@u^t@=8s@axc41ml*f=s'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
TESTING = sys.argv[1:2] == ['test']

SITE_ID = 1
# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    'website',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.google',
    'django_gravatar',
    'email_obfuscator',
    'import_export',
    'comments',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'rollbar.contrib.django.middleware.RollbarNotifierMiddleware',
 
)

TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

if DEBUG and not TESTING:
    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.logging.LoggingPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
    ]

    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
        "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    }

    INSTALLED_APPS += ('debug_toolbar',)

    MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)

ROOT_URLCONF = 'bugheist.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': True,
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.media',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

WSGI_APPLICATION = 'bugheist.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

LANGUAGES = (
    ('en', _('English')),
    ('fr', _('French')),
    ('zh-cn', _('Chinese')),
    ('de', _('German')),
)

MEDIA_ROOT = "media"
MEDIA_URL = '/media/'
# Update database configuration with $DATABASE_URL.
db_from_env = dj_database_url.config(conn_max_age=500)
DATABASES['default'].update(db_from_env)

EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025
# python -m smtpd -n -c DebuggingServer localhost:1025
# if DEBUG:
#    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


if 'DATABASE_URL' in os.environ:
    DEBUG = False
    EMAIL_HOST = 'smtp.sendgrid.net'
    EMAIL_HOST_USER = os.environ.get('SENDGRID_USERNAME', 'blank')
    EMAIL_HOST_PASSWORD = os.environ.get('SENDGRID_PASSWORD', 'blank')
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    if not TESTING:
        SECURE_SSL_REDIRECT = True

    GS_ACCESS_KEY_ID = os.environ.get('GS_ACCESS_KEY_ID', 'blank')
    GS_SECRET_ACCESS_KEY = os.environ.get('GS_SECRET_ACCESS_KEY', 'blank')
    GS_BUCKET_NAME = 'bhfiles'
    DEFAULT_FILE_STORAGE = 'storages.backends.gs.GSBotoStorage'
    GS_FILE_OVERWRITE = False
    GS_QUERYSTRING_AUTH = False
    MEDIA_URL = "https://bhfiles.storage.googleapis.com/"

    ROLLBAR = {
        'access_token': os.environ.get('ROLLBAR_ACCESS_TOKEN', 'blank'),
        'environment': 'development' if DEBUG else 'production',
        'root': BASE_DIR,
        'exception_level_filters': [
            (Http404, 'warning')
        ]
    }
    import rollbar

    rollbar.init(**ROLLBAR)

# local dev needs to set SMTP backend or fail at startup
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "optional"

# Honor the 'X-Forwarded-Proto' header for request.is_secure()

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'staticfiles')
STATIC_URL = '/static/'

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'static'),
)

ABSOLUTE_URL_OVERRIDES = {
    'auth.user': lambda u: "/profile/%s/" % u.username,
}

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/
STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'

LOGIN_REDIRECT_URL = "/"

LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'testlogger': {
            'handlers': ['console'],
            'level': 'INFO',
        }
    },
}

USERS_AVATAR_PATH = 'avatars'
AVATAR_PATH = os.path.join(MEDIA_ROOT, USERS_AVATAR_PATH)

if not os.path.exists(AVATAR_PATH):
    os.makedirs(AVATAR_PATH)
