from __future__ import unicode_literals
import os


# From https://raw.githubusercontent.com/tomchristie/django-rest-framework/master/tests/conftest.py

def pytest_configure():
    from django.conf import settings

    kwargs = {}
    use_custom_model = os.environ.get('USE_CUSTOM_MODEL') == 'true'

    # This is for tests only, we need to handle that the Foo/Bar models needs a different primary key when running
    # tests with STAR_RATINGS_RATING_MODEL, setting to leverage in tests.
    kwargs['FOO_MODEL'] = 'tests.Foo'
    kwargs['BAR_MODEL'] = 'tests.Bar'

    if use_custom_model:
        kwargs['STAR_RATINGS_RATING_MODEL'] = 'tests.MyRating'
        kwargs['FOO_MODEL'] = 'tests.FooWithUUID'
        kwargs['BAR_MODEL'] = 'tests.BarWithUUID'

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3',
                               'NAME': ':memory:'}},
        SECRET_KEY='not very secret in tests',
        USE_I18N=True,
        USE_L10N=True,
        STATIC_URL='/static/',
        ROOT_URLCONF='tests.urls',
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.debug',
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                    ],
                },
            }
        ],
        MIDDLEWARE_CLASSES=(
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ),
        MIDDLEWARE=(
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ),
        INSTALLED_APPS=(
            'django.contrib.auth',
            'django.contrib.admin',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.messages',
            'django.contrib.staticfiles',

            'model_utils',

            'tests',
            'star_ratings',
        ),
        PASSWORD_HASHERS=(
            'django.contrib.auth.hashers.SHA1PasswordHasher',
            'django.contrib.auth.hashers.PBKDF2PasswordHasher',
            'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
            'django.contrib.auth.hashers.MD5PasswordHasher',
            'django.contrib.auth.hashers.CryptPasswordHasher',
        ),

        STAR_RATINGS_RERATE=True,
        **kwargs
    )

    try:
        import django
        django.setup()
    except AttributeError:
        pass
