import os

from .base import *

DEBUG = os.getenv("DEBUG", 'False').lower() in ('true', '1', 't')
SECRET_KEY = os.getenv('SECRET_KEY')
# see https://github.com/jacobian/dj-database-url
# Configure your database from DATABASE_URL env var
# DATABASES = {
#     'default': dj_database_url.config(conn_max_age=60)
# }
STATIC_ROOT = os.getenv('STATIC_ROOT', STATIC_ROOT)
MEDIA_ROOT = os.getenv('MEDIA_ROOT', MEDIA_ROOT)
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
WAGTAILADMIN_BASE_URL = os.getenv('WAGTAILADMIN_BASE_URL', WAGTAILADMIN_BASE_URL)
OIDC_OP_AUTHORIZATION_ENDPOINT = os.getenv('OIDC_OP_AUTHORIZATION_ENDPOINT')
OIDC_OP_TOKEN_ENDPOINT = os.getenv('OIDC_OP_TOKEN_ENDPOINT')
OIDC_OP_USER_ENDPOINT = os.getenv('OIDC_OP_USER_ENDPOINT')
OIDC_RP_CLIENT_ID = os.getenv('OIDC_RP_CLIENT_ID')
OIDC_RP_CLIENT_SECRET = os.getenv('OIDC_RP_CLIENT_SECRET')
OIDC_OP_JWKS_ENDPOINT = os.getenv('OIDC_OP_JWKS_ENDPOINT')
OIDC_OP_NAME = os.getenv('OIDC_OP_NAME')
RECAPTCHA_PUBLIC_KEY = os.getenv('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = os.getenv('RECAPTCHA_PRIVATE_KEY')

try:
    from .local import *
except ImportError:
    pass
