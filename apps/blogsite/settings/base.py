"""
Django settings for blogsite project.

Generated by 'django-admin startproject' using Django 3.2.9.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from pathlib import Path

import dj_database_url
import sys

PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_DIR.parent

BLOGSITE_PAGE_SIZE = int(os.getenv('BLOGSITE_PAGE_SIZE', '8'))

try:
    RUNNING_DEVSERVER = (sys.argv[1] == 'runserver')
except IndexError:
    RUNNING_DEVSERVER = False

RUNNING_TEST = 'test' in sys.argv

if RUNNING_DEVSERVER or RUNNING_TEST:
    INTERNAL_IPS = ['127.0.0.1', '[::1]']
    DEBUG = True
else:
    DEBUG = False

# ALLOWED_HOSTS = ['.localhost', '127.0.0.1', '[::1]']

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

DEFAULT_FROM_EMAIL = SERVER_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'webmaster@g10f.de')
EVENT_REGISTRATION_EMAIL = os.getenv('EVENT_REGISTRATION_EMAIL', DEFAULT_FROM_EMAIL)
EVENT_REGISTRATION_PHONE_NUMBER = '+49-123-45678'
# List seperated by ; with tuples seperated by , e.g 'Admin 1,admin1@example.com;Admin 2,admin2@example.com'
ADMINS = [tuple(admin.split(',')) for admin in os.getenv('ADMINS', 'Gunnar Scherf,mail@g10f.de').split(';')]
EMAIL_SUBJECT_PREFIX = os.getenv('EMAIL_SUBJECT_PREFIX', '[BlogSite] ')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '25'))
LOGO_SIZE = os.getenv('LOGO_SIZE', 'normal')  # small, normal or big
HERO_WITH_TITLE = os.getenv('HERO_WITH_TITLE', 'True').lower() in ('true', '1', 't')
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# Application definition

INSTALLED_APPS = [
    'blogsite',
    'blogsite.base',
    'blogsite.search',
    'blogsite.blog',
    'oidc',

    'wagtail.contrib.settings',
    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    # 'wagtail.contrib.styleguide',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',
    'wagtail',
    'wagtail.locales',
    # "wagtail.contrib.modeladmin",
    'wagtail.contrib.simple_translation',
    "wagtail.contrib.routable_page",
    "wagtail.contrib.frontend_cache",

    'modelcluster',
    'taggit',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    "django.contrib.sitemaps",
    "django.forms",  # for overwriting attr.html

    'mozilla_django_oidc',
    'django_recaptcha',
]

# Add 'mozilla_django_oidc' authentication backend
AUTHENTICATION_BACKENDS = [
    'oidc.backend.AuthenticationBackend',
    "django.contrib.auth.backends.ModelBackend"
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    "core.middleware.PathBasedCsrfViewMiddleware",
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
]

ROOT_URLCONF = 'blogsite.urls'

if DEBUG:
    # don't use cached loader
    LOADERS = [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]
else:
    LOADERS = [
        ('django.template.loaders.cached.Loader', (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        )),
    ]

TEMPLATE_DIRS = (os.getenv('TEMPLATE_DIRS', []) + [BASE_DIR / 'templates'])

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': TEMPLATE_DIRS,
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'blogsite.context_processors.settings',
                'wagtail.contrib.settings.context_processors.settings'
            ],
            'loaders': LOADERS,
            'debug': DEBUG
        },
    },
]

# for adding bootstrap class form-control
# https://docs.djangoproject.com/en/4.2/ref/settings/#std-setting-FORM_RENDERER
FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

WSGI_APPLICATION = 'blogsite.wsgi.application'

# Database
# postgres://USER:PASSWORD@HOST:PORT/NAME
# sqlite:////full/path/to/your/database/file.sqlite
# see https://github.com/jacobian/dj-database-url
# Configure your database from DATABASE_URL env var
DATABASES = {
    'default': dj_database_url.config(default=f"sqlite:///{BASE_DIR.parent / 'data/blogsite.db'}", conn_max_age=60)
}

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    }
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = os.getenv('LANGUAGE_CODE', 'de')

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = [BASE_DIR / 'blogsite' / 'locale']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
]

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# ManifestStaticFilesStorage is recommended in production, to prevent outdated
# JavaScript / CSS assets being served from cache (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/3.2/ref/contrib/staticfiles/#manifeststaticfilesstorage
if RUNNING_TEST:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

STATIC_URL = '/static/'
MEDIA_URL = os.getenv('MEDIA_URL', '/media/')

STATIC_ROOT = os.getenv('STATIC_ROOT', BASE_DIR.parent / 'htdocs/static')
MEDIA_ROOT = os.getenv('MEDIA_ROOT', BASE_DIR.parent / 'htdocs/media')
WHITENOISE_ROOT = os.path.join(STATIC_ROOT, 'root')

# Wagtail settings
WAGTAIL_I18N_ENABLED = os.getenv('WAGTAIL_I18N_ENABLED', 'True').lower() in ('true', '1', 't')
WAGTAIL_SITE_NAME = os.getenv('WAGTAIL_SITE_NAME', 'The Blog Site')

WAGTAILIMAGES_MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # i.e. 20MB

WAGTAIL_CONTENT_LANGUAGES = LANGUAGES = [
    ('en', "English"),
    ('de', "German"),
    ('pl', "Polish")
]
# Search
# https://docs.wagtail.io/en/stable/topics/search/backends.html
WAGTAILSEARCH_BACKENDS = {
    'default': {
        'BACKEND': 'wagtail.search.backends.database',
    }
}

WAGTAILFRONTENDCACHE = {
    'varnish': {
        'BACKEND': 'wagtail.contrib.frontend_cache.backends.HTTPBackend',
        'LOCATION': os.getenv('WAGTAILFRONTENDCACHE_LOCATION', 'http://localhost:6081'),
    },
}

WAGTAILFRONTENDCACHE_LANGUAGES = [l[0] for l in LANGUAGES]

WAGTAILIMAGES_FEATURE_DETECTION_ENABLED = False

# Base URL to use when referring to full URLs within the Wagtail admin backend -
# e.g. in notification emails. Don't include '/admin' or a trailing slash
WAGTAILADMIN_BASE_URL = os.getenv('WAGTAILADMIN_BASE_URL', 'https://example.com')

# We require CSRF only on authenticated paths. This setting is handled by our
# core.middleware.PathBasedCsrfViewMiddleware.
#
# Any paths listed here that are public-facing will receive an "
# "Edge-Control: no-store" header from our
# core.middleware.DownstreamCacheControlMiddleware and will not be cached.
CSRF_REQUIRED_PATHS = (
    "/login",
    "/admin",
    "/django-admin",
)

# https://django-taggit.readthedocs.io/en/latest/changelog.html#id2
TAGGIT_STRIP_UNICODE_WHEN_SLUGIFYING = True

# mozilla-django-oidc settings
LOGIN_REDIRECT_URL = "/admin/"
LOGOUT_REDIRECT_URL = "/admin/"
OIDC_RP_SIGN_ALGO = 'RS256'
OIDC_STORE_ID_TOKEN = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple' if DEBUG else 'verbose'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'level': 'DEBUG' if DEBUG else 'INFO',
        'handlers': ['console', 'mail_admins'],
    },
}
