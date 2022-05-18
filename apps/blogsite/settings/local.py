from .base import *   # noqa

# Override settings here
# SECRET_KEY = '$q(y#(8_8iem@$)cfv76*1#!v_0!j4l)+0u(b0hm+zoz2)n=6r'
# database_url = "postgres://blogsite:blogsite@localhost:5432/blogsite"
database_url = f"sqlite:///{BASE_DIR.parent / 'data/blogsite.db'}"
DATABASES = {
    'default': dj_database_url.config(default=database_url)
}
STATIC_ROOT = BASE_DIR.parent / 'data/static'
MEDIA_ROOT = BASE_DIR.parent / 'data/media'

OIDC_OP_AUTHORIZATION_ENDPOINT = "https://accounts.afd-team.de/oauth2/authorize/"
OIDC_OP_TOKEN_ENDPOINT = "https://accounts.afd-team.de/oauth2/token/"
OIDC_OP_USER_ENDPOINT = "https://accounts.afd-team.de/api/v2/users/me/"

OIDC_RP_CLIENT_ID = '2e8f7879-dce5-40ac-846a-7d0c3d908d96'
OIDC_RP_CLIENT_SECRET = 'k3TMazCbsWKPMTsLIqytjrJtK1qBY0'
OIDC_OP_JWKS_ENDPOINT = "https://accounts.afd-team.de/oauth2/jwks/"
OIDC_RP_SIGN_ALGO = 'RS256'
OIDC_OP_NAME = "AfD SSO"
