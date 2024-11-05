"""
Django settings for gettingstarted project, on Heroku. For more info, see:
https://github.com/heroku/heroku-django-template
For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/
For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# from google.oauth2 import service_account
import os
import sys

import dj_database_url
import environ
from django.utils.translation import gettext_lazy as _

env = environ.Env()
# reading .env file
environ.Env.read_env()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "blank")


PROJECT_NAME = "BLT"
DOMAIN_NAME = "blt.owasp.org"
FQDN = "blt.owasp.org"
DOMAIN_NAME_PREVIOUS = os.environ.get("DOMAIN_NAME_PREVIOUS", "BLT")
# else:
#     # Default values if hostname does not match
#     PROJECT_NAME = os.environ.get("PROJECT_NAME", "BLT")
#     DOMAIN_NAME = os.environ.get("DOMAIN_NAME", "127.0.0.1")
#     FQDN = "www." + DOMAIN_NAME

PROJECT_NAME_LOWER = PROJECT_NAME.lower()
PROJECT_NAME_UPPER = PROJECT_NAME.upper()

ADMIN_URL = os.environ.get("ADMIN_URL", "admin")
PORT = os.environ.get("PORT", "8000")
DEFAULT_FROM_EMAIL = os.environ.get("FROM_EMAIL", "test@localhost")
SERVER_EMAIL = os.environ.get("FROM_EMAIL", "test@localhost")


EMAIL_TO_STRING = PROJECT_NAME + " <" + SERVER_EMAIL + ">"
BLOG_URL = os.environ.get("BLOG_URL", "https://owasp.org/www-project-bug-logging-tool/")
FACEBOOK_URL = os.environ.get("FACEBOOK_URL", "https://www.facebook.com/groups/owaspfoundation/")
TWITTER_URL = os.environ.get("TWITTER_URL", "https://twitter.com/owasp")
GITHUB_URL = os.environ.get("GITHUB_URL", "https://github.com/OWASP/BLT")
EXTENSION_URL = os.environ.get("EXTENSION_URL", "https://github.com/OWASP/BLT")

ADMINS = (("Admin", DEFAULT_FROM_EMAIL),)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: change this before deploying to production!
SECRET_KEY = "i+acxn5(akgsn!sr4^qgf(^m&*@+g1@u^t@=8s@axc41ml*f=s"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
TESTING = sys.argv[1:2] == ["test"]

SITE_ID = 1
# Application definition

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
    "website",
    "company",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.github",
    "allauth.socialaccount.providers.facebook",
    "allauth.socialaccount.providers.google",
    "django_gravatar",
    "email_obfuscator",
    "import_export",
    "comments",
    "annoying",
    "rest_framework",
    "django_filters",
    "rest_framework.authtoken",
    # "django_cron",
    "mdeditor",
    # "bootstrap_datepicker_plus",
    "tz_detect",
    # "tellme",
    "star_ratings",
    "drf_yasg",
    "captcha",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "blog",
)


# CRON_CLASSES = ["website.views.CreateIssue"]

MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "tz_detect.middleware.TimezoneMiddleware",
    "blt.middleware.ip_restrict.IPRestrictMiddleware",
)

TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

if DEBUG and not TESTING:
    DEBUG_TOOLBAR_PANELS = [
        "debug_toolbar.panels.versions.VersionsPanel",
        "debug_toolbar.panels.timer.TimerPanel",
        "debug_toolbar.panels.settings.SettingsPanel",
        "debug_toolbar.panels.headers.HeadersPanel",
        "debug_toolbar.panels.request.RequestPanel",
        "debug_toolbar.panels.sql.SQLPanel",
        "debug_toolbar.panels.staticfiles.StaticFilesPanel",
        "debug_toolbar.panels.templates.TemplatesPanel",
        "debug_toolbar.panels.cache.CachePanel",
        "debug_toolbar.panels.signals.SignalsPanel",
        "debug_toolbar.panels.logging.LoggingPanel",
        "debug_toolbar.panels.redirects.RedirectsPanel",
    ]

    DEBUG_TOOLBAR_CONFIG = {
        "INTERCEPT_REDIRECTS": False,
        "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    }

    INSTALLED_APPS += ("debug_toolbar",)

    MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)

ROOT_URLCONF = "blt.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {
            "debug": DEBUG,
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.media",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
            ],
            "loaders": [
                (
                    "django.template.loaders.cached.Loader",
                    [
                        "django.template.loaders.filesystem.Loader",
                        "django.template.loaders.app_directories.Loader",
                    ],
                ),
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

# SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# CACHES = {
#    'default': {
#        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
#        'LOCATION': 'cache_table',
#    }
# }


REST_AUTH = {"SESSION_LOGIN": False}
CONN_MAX_AGE = None

WSGI_APPLICATION = "blt.wsgi.application"

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"),)

LANGUAGES = (
    ("en", _("English")),
    ("fr", _("French")),
    ("zh-cn", _("Chinese")),
    ("de", _("German")),
    ("ja", _("Japanese")),
    ("ru", _("Russian")),
    ("hi", _("Hindi")),
)

MEDIA_ROOT = "media"
MEDIA_URL = "/media/"
# Update database configuration with $DATABASE_URL.
db_from_env = dj_database_url.config(conn_max_age=500)
DATABASES["default"].update(db_from_env)

EMAIL_HOST = "localhost"
EMAIL_PORT = 1025
# python -m smtpd -n -c DebuggingServer localhost:1025
# if DEBUG:
#    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

REPORT_EMAIL = os.environ.get("REPORT_EMAIL", "blank")
REPORT_EMAIL_PASSWORD = os.environ.get("REPORT_PASSWORD", "blank")
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
if "DATABASE_URL" in os.environ:
    DEBUG = False
    EMAIL_HOST = "smtp.sendgrid.net"
    EMAIL_HOST_USER = os.environ.get("SENDGRID_USERNAME", "blank")
    EMAIL_HOST_PASSWORD = os.environ.get("SENDGRID_PASSWORD", "blank")
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    if not TESTING:
        SECURE_SSL_REDIRECT = True

    GS_ACCESS_KEY_ID = os.environ.get("GS_ACCESS_KEY_ID", "blank")
    GS_SECRET_ACCESS_KEY = os.environ.get("GS_SECRET_ACCESS_KEY", "blank")
    GOOGLE_APPLICATION_CREDENTIALS = "/app/google-credentials.json"

    GS_BUCKET_NAME = "bhfiles"
    DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
    GS_FILE_OVERWRITE = False
    GS_QUERYSTRING_AUTH = False
    MEDIA_URL = "https://bhfiles.storage.googleapis.com/"

    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN", "https://key.ingest.sentry.io/project"),
        integrations=[DjangoIntegration()],
        send_default_pii=True,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        release=os.environ.get("HEROKU_RELEASE_VERSION", default=""),
    )

else:
    if not TESTING:
        DEBUG = True

# local dev needs to set SMTP backend or fail at startup
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "optional"

# Honor the 'X-Forwarded-Proto' header for request.is_secure()

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Allow all host headers
ALLOWED_HOSTS = [
    "." + DOMAIN_NAME,
    "127.0.0.1",
    "localhost",
    "0.0.0.0",
    "blt.owasp.org",
    "." + DOMAIN_NAME_PREVIOUS,
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_ROOT = os.path.join(PROJECT_ROOT, "staticfiles")
STATIC_URL = "/static/"

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
    os.path.join(BASE_DIR, "website", "static"),
    os.path.join(BASE_DIR, "company", "static"),
)

ABSOLUTE_URL_OVERRIDES = {
    "auth.user": lambda u: "/profile/%s/" % u.username,
}

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

LOGIN_REDIRECT_URL = "/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}
USERS_AVATAR_PATH = "avatars"
AVATAR_PATH = os.path.join(MEDIA_ROOT, USERS_AVATAR_PATH)

if not os.path.exists(AVATAR_PATH):
    os.makedirs(AVATAR_PATH)

if DEBUG or TESTING:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
else:
    if os.environ.get("MEMCACHIER_SERVERS", ""):
        os.environ["MEMCACHE_SERVERS"] = os.environ.get("MEMCACHIER_SERVERS", "").replace(",", ";")
        os.environ["MEMCACHE_USERNAME"] = os.environ.get("MEMCACHIER_USERNAME", "")
        os.environ["MEMCACHE_PASSWORD"] = os.environ.get("MEMCACHIER_PASSWORD", "")

        CACHES = {
            "default": {
                "BACKEND": "django_pylibmc.memcached.PyLibMCCache",
                "BINARY": True,
                "TIMEOUT": None,
                "OPTIONS": {
                    "tcp_nodelay": True,
                    "tcp_keepalive": True,
                    "connect_timeout": 2000,
                    "send_timeout": 750 * 1000,
                    "receive_timeout": 750 * 1000,
                    "_poll_timeout": 2000,
                    "ketama": True,
                    "remove_failed": 1,
                    "retry_timeout": 2,
                    "dead_timeout": 30,
                },
            }
        }
    else:
        CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

if DEBUG or TESTING:
    anon_throttle = 100000
    user_throttle = 100000

else:
    anon_throttle = 100
    user_throttle = 1000

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework.authentication.TokenAuthentication",),
    "PAGE_SIZE": 10,
    "DEFAULT_THROTTLE_RATES": {
        "anon": f"{anon_throttle}/day",
        "user": f"{user_throttle}/day",
    },
}

SOCIALACCOUNT_PROVIDERS = {
    "github": {
        "SCOPE": ["user:email"],
        "AUTH_PARAMS": {"access_type": "online"},
    },
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    },
    "facebook": {
        "METHOD": "oauth2",
        "SCOPE": ["email"],
        "FIELDS": [
            "id",
            "email",
            "name",
            "first_name",
            "last_name",
            "verified",
            "locale",
            "timezone",
            "link",
        ],
        "EXCHANGE_TOKEN": True,
        "LOCALE_FUNC": lambda request: "en_US",
        "VERIFIED_EMAIL": False,
        "VERSION": "v7.0",
    },
}

ACCOUNT_ADAPTER = "allauth.account.adapter.DefaultAccountAdapter"
SOCIALACCOUNT_ADAPTER = "allauth.socialaccount.adapter.DefaultSocialAccountAdapter"

X_FRAME_OPTIONS = "SAMEORIGIN"

MDEDITOR_CONFIGS = {
    "default": {
        "language": "en",
        "toolbar": [
            "undo",
            "redo",
            "|",
            "bold",
            "del",
            "italic",
            "quote",
            "ucwords",
            "uppercase",
            "lowercase",
            "|",
            "h1",
            "h2",
            "h3",
            "h5",
            "h6",
            "|",
            "list-ul",
            "list-ol",
            "hr",
            "|",
            "link",
            "reference-link",
            "code",
            "code-block",
            "table",
            "datetime",
            "||",
            "preview",
            "fullscreen",
        ],
        "watch": False,
    }
}

# SuperUser Details

SUPERUSER_USERNAME = env("SUPERUSER", default="admin123")
SUPERUSER_EMAIL = env("SUPERUSER_MAIL", default="admin123@gmail.com")
SUPERUSER_PASSWORD = env("SUPERUSER_PASSWORD", default="admin@123")


SUPERUSERS = ((SUPERUSER_USERNAME, SUPERUSER_EMAIL, SUPERUSER_PASSWORD),)

STRIPE_LIVE_PUBLIC_KEY = os.environ.get("STRIPE_LIVE_PUBLIC_KEY", "<your publishable key>")
STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "<your secret key>")
STRIPE_TEST_PUBLIC_KEY = os.environ.get(
    "STRIPE_TEST_PUBLIC_KEY",
    "pk_test_12345",
)
STRIPE_TEST_SECRET_KEY = os.environ.get(
    "STRIPE_TEST_SECRET_KEY",
    "sk_test_12345",
)
STRIPE_LIVE_MODE = False  # Change to True in production

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# CALLBACK_URL_FOR_GITHUB = os.environ.get(
#     "CALLBACK_URL_FOR_GITHUB", default="https://www." + DOMAIN_NAME +"/")

# CALLBACK_URL_FOR_GOOGLE = os.environ.get(
#     "CALLBACK_URL_FOR_GOOGLE", default="https://www." + DOMAIN_NAME +"/")

# CALLBACK_URL_FOR_FACEBOOK = os.environ.get(
#     "CALLBACK_URL_FOR_FACEBOOK", default="https://www." + DOMAIN_NAME +"/")


# allow captcha bypass during test
IS_TEST = False
if "test" in sys.argv:
    CAPTCHA_TEST_MODE = True
    IS_TEST = True


# Twitter

BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
APP_KEY = os.environ.get("APP_KEY")
APP_KEY_SECRET = os.environ.get("APP_KEY_SECRET")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")

# USPTO

USPTO_API = os.environ.get("USPTO_API")


BITCOIN_RPC_USER = os.environ.get("BITCOIN_RPC_USER", "yourusername")
BITCOIN_RPC_PASSWORD = os.environ.get("BITCOIN_RPC_PASSWORD", "yourpassword")
BITCOIN_RPC_HOST = os.environ.get("BITCOIN_RPC_HOST", "localhost")
BITCOIN_RPC_PORT = os.environ.get("BITCOIN_RPC_PORT", "8332")
