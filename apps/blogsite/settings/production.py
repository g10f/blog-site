import os

from .base import *

THEME = os.getenv('THEME')
if THEME:
    INSTALLED_APPS = [THEME] + INSTALLED_APPS

DEBUG = os.getenv("DEBUG", 'False').lower() in ('true', '1', 't')
# see https://github.com/jacobian/dj-database-url
# Configure your database from DATABASE_URL env var
# DATABASES = {
#     'default': dj_database_url.config(conn_max_age=60)
# }
STATIC_ROOT = os.getenv('STATIC_ROOT', STATIC_ROOT)
MEDIA_ROOT = os.getenv('MEDIA_ROOT', MEDIA_ROOT)
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
OIDC_OP_AUTHORIZATION_ENDPOINT = os.getenv('OIDC_OP_AUTHORIZATION_ENDPOINT', '')
OIDC_OP_TOKEN_ENDPOINT = os.getenv('OIDC_OP_TOKEN_ENDPOINT', '')
OIDC_OP_USER_ENDPOINT = os.getenv('OIDC_OP_USER_ENDPOINT', '')
OIDC_RP_CLIENT_ID = os.getenv('OIDC_RP_CLIENT_ID', '')
OIDC_RP_CLIENT_SECRET = os.getenv('OIDC_RP_CLIENT_SECRET', '')
OIDC_OP_JWKS_ENDPOINT = os.getenv('OIDC_OP_JWKS_ENDPOINT', '')
OIDC_OP_LOGOUT_URL_METHOD = os.getenv('OIDC_OP_LOGOUT_URL_METHOD', '')
OIDC_OP_NAME = os.getenv('OIDC_OP_NAME', '')


try:
    from .local import *
except ImportError:
    pass
