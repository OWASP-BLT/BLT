import json
import os
import sys

import dj_database_url
import environ

# Initialize Sentry
import sentry_sdk
from django.utils.translation import gettext_lazy as _
from google.oauth2 import service_account
from sentry_sdk.integrations.django import DjangoIntegration

environ.Env.read_env()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
env = environ.Env()
env_file = os.path.join(BASE_DIR, ".env")
environ.Env.read_env(env_file)

print(f"Reading .env file from {env_file}")
print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'not set')}")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "blank")
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "blank")


PROJECT_NAME = "BLT"
DOMAIN_NAME = "blt.owasp.org"
FQDN = "blt.owasp.org"
DOMAIN_NAME_PREVIOUS = os.environ.get("DOMAIN_NAME_PREVIOUS", "BLT")

PROJECT_NAME_LOWER = PROJECT_NAME.lower()
PROJECT_NAME_UPPER = PROJECT_NAME.upper()

ADMIN_URL = os.environ.get("ADMIN_URL", "admin")
PORT = os.environ.get("PORT", "8000")
DEFAULT_FROM_EMAIL = os.environ.get("FROM_EMAIL", "blt-support@owasp.org")
SERVER_EMAIL = os.environ.get("FROM_EMAIL", "blt-support@owasp.org")


EMAIL_TO_STRING = PROJECT_NAME + " <" + SERVER_EMAIL + ">"
BLOG_URL = os.environ.get("BLOG_URL", FQDN + "/blog/")
FACEBOOK_URL = os.environ.get("FACEBOOK_URL", "https://www.facebook.com/groups/owaspfoundation/")
TWITTER_URL = os.environ.get("TWITTER_URL", "https://twitter.com/owasp_blt")
GITHUB_URL = os.environ.get("GITHUB_URL", "https://github.com/OWASP/BLT")
EXTENSION_URL = os.environ.get("EXTENSION_URL", "https://github.com/OWASP/BLT-Extension")

ADMINS = (("Admin", DEFAULT_FROM_EMAIL),)

SECRET_KEY = "i+acxn5(akgsn!sr4^qgf(^m&*@+g1@u^t@=8s@axc41ml*f=s"

DEBUG = False
TESTING = sys.argv[1:2] == ["test"]

SITE_ID = 1

# Scout settings
SCOUT_MONITOR = True
SCOUT_KEY = os.environ.get("SCOUT_KEY")
SCOUT_NAME = PROJECT_NAME


INSTALLED_APPS = (
    # "scout_apm.django",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
    "website",
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
    "mdeditor",
    "tz_detect",
    "star_ratings",
    "drf_yasg",
    "captcha",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "storages",
    "channels",
)

if DEBUG:
    INSTALLED_APPS += ("livereload",)

SOCIAL_AUTH_GITHUB_KEY = os.environ.get("GITHUB_CLIENT_ID", "blank")
SOCIAL_AUTH_GITHUB_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "blank")


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

if DEBUG:
    MIDDLEWARE += ["livereload.middleware.LiveReloadScript"]

BLUESKY_USERNAME = env("BLUESKY_USERNAME", default="default_username")
BLUESKY_PASSWORD = env("BLUESKY_PASSWORD", default="default_password")
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
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ]
            if DEBUG
            else [
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


REST_AUTH = {"SESSION_LOGIN": False}
CONN_MAX_AGE = 0

# WSGI_APPLICATION = "blt.wsgi.application"

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
db_from_env = dj_database_url.config(conn_max_age=500)


# Fetch the Sentry DSN from environment variables
SENTRY_DSN = os.environ.get("SENTRY_DSN")

if SENTRY_DSN:
    print(f"Initializing Sentry with DSN: {SENTRY_DSN}")
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        send_default_pii=True,
        traces_sample_rate=1.0 if DEBUG else 0.2,
        profiles_sample_rate=1.0 if DEBUG else 0.2,
        environment="development" if DEBUG else "production",
        release=os.environ.get("HEROKU_RELEASE_VERSION", "local"),
    )
else:
    print("Sentry DSN not set. Skipping Sentry initialization.")

EMAIL_HOST = "localhost"
EMAIL_PORT = 1025


REPORT_EMAIL = os.environ.get("REPORT_EMAIL", "blank")
REPORT_EMAIL_PASSWORD = os.environ.get("REPORT_PASSWORD", "blank")

if "DYNO" in os.environ:  # for Heroku
    DEBUG = False
    EMAIL_HOST = "smtp.sendgrid.net"
    EMAIL_HOST_USER = os.environ.get("SENDGRID_USERNAME", "blank")
    EMAIL_HOST_PASSWORD = os.environ.get("SENDGRID_PASSWORD", "blank")
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    if not TESTING:
        SECURE_SSL_REDIRECT = True

    # import logging

    # logging.basicConfig(level=logging.DEBUG)

    GS_BUCKET_NAME = "bhfiles"

    GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

    if not GOOGLE_CREDENTIALS:
        raise Exception("GOOGLE_CREDENTIALS environment variable is not set.")

    GS_CREDENTIALS = service_account.Credentials.from_service_account_info(json.loads(GOOGLE_CREDENTIALS))

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {
                "credentials": GS_CREDENTIALS,
                "bucket_name": GS_BUCKET_NAME,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
        },
    }

    GS_FILE_OVERWRITE = False
    GS_QUERYSTRING_AUTH = False
    GS_DEFAULT_ACL = None
    MEDIA_URL = "https://bhfiles.storage.googleapis.com/"

else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
        },
    }
    DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
    if not TESTING:
        DEBUG = True

    # use this to debug emails locally
    # python -m smtpd -n -c DebuggingServer localhost:1025
    # if DEBUG:
    #     EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

if not db_from_env:
    print("no database url detected in settings, using sqlite")
else:
    DATABASES["default"] = dj_database_url.config(conn_max_age=0, ssl_require=False)

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_FORMS = {"signup": "website.forms.SignupFormWithCaptcha"}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "0.0.0.0",
]
ALLOWED_HOSTS.extend(os.environ.get("ALLOWED_HOSTS", "").split(","))


STATIC_ROOT = os.path.join(PROJECT_ROOT, "staticfiles")
STATIC_URL = "/static/"

STATICFILES_DIRS = (os.path.join(BASE_DIR, "website", "static"),)

ABSOLUTE_URL_OVERRIDES = {
    "auth.user": lambda u: "/profile/%s/" % u.username,
}

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_ON_GET = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"},
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "stream": "ext://sys.stdout",  # Explicitly use stdout
        },
        "mail_admins": {"level": "ERROR", "class": "django.utils.log.AdminEmailHandler"},
    },
    "root": {
        "level": "DEBUG",  # Set to DEBUG to show all messages
        "handlers": ["console"],
    },
    "loggers": {
        "django": {
            "handlers": ["console", "mail_admins"],
            "level": "INFO",
            "propagate": True,  # Changed to True to show in root logger
        },
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,  # Changed to True to show in root logger
        },
        "website": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
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

if DEBUG or TESTING:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }
else:
    # temp to check memory usage
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

    # CACHES = {
    #     "default": {
    #         "BACKEND": "django_redis.cache.RedisCache",
    #         "LOCATION": os.environ.get("REDISCLOUD_URL"),
    #         "OPTIONS": {
    #             "CLIENT_CLASS": "django_redis.client.DefaultClient",
    #         },
    #     }
    # }

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
        "SCOPE": ["user", "repo"],
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

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

IS_TEST = False
if "test" in sys.argv:
    CAPTCHA_TEST_MODE = True
    IS_TEST = True

# Twitter API - we can remove these - update names to have twitter_x or bluesky_x
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
APP_KEY = os.environ.get("APP_KEY")
APP_KEY_SECRET = os.environ.get("APP_KEY_SECRET")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")

USPTO_API = os.environ.get("USPTO_API")


BITCOIN_RPC_USER = os.environ.get("BITCOIN_RPC_USER", "yourusername")
BITCOIN_RPC_PASSWORD = os.environ.get("BITCOIN_RPC_PASSWORD", "yourpassword")
BITCOIN_RPC_HOST = os.environ.get("BITCOIN_RPC_HOST", "localhost")
BITCOIN_RPC_PORT = os.environ.get("BITCOIN_RPC_PORT", "8332")

ASGI_APPLICATION = "blt.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get("REDISCLOUD_URL")],
            # "hosts": [("127.0.0.1", 6379)],
        },
    },
}
if DEBUG:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }

ORD_SERVER_URL = os.getenv("ORD_SERVER_URL", "http://localhost:9001")  # Default to local for development
SOCIALACCOUNT_STORE_TOKENS = True


