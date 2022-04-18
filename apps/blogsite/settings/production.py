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
BASE_URL = os.getenv('BASE_URL', BASE_URL)

try:
    from .local import *
except ImportError:
    pass
