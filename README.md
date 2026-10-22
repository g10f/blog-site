The Blog Site
=============
Django + Wagtail CMS for blogs with events. Multi-language (de, en, pl), optional OpenID Connect login
for the admin and optional event booking with Campai.

The image `ghcr.io/g10f/blog-site` is the base image for theme repositories: a theme builds
`FROM ghcr.io/g10f/blog-site:<version>`, adds a small Django app with its templates and styles and
selects it with `THEME=<app>`.

Configuration
-------------
The settings are read from environment variables, the most important ones:

| Variable                           | Description                                                   |
|------------------------------------|---------------------------------------------------------------|
| `DATABASE_URL`                     | database, default is the SQLite file `data/blogsite.db`       |
| `SECRET_KEY`                       | Django secret key                                             |
| `ALLOWED_HOSTS`                    | comma separated list                                          |
| `THEME`                            | Django app of the theme                                       |
| `WAGTAIL_SITE_NAME`                | name of the site in the admin                                 |
| `WAGTAILADMIN_BASE_URL`            | base URL of the admin, used in mails                          |
| `WAGTAILFRONTENDCACHE_LOCATION`    | Varnish cache that is purged on publishing                    |
| `LANGUAGE_CODE`                    | default language, `de`                                        |
| `OIDC_OP_*`, `OIDC_RP_*`           | OpenID Connect login for the admin                            |
| `CAMPAI_*`                         | event booking with Campai                                     |
| `EMAIL_HOST`, `DEFAULT_FROM_EMAIL` | mail server and sender                                        |

See `apps/blogsite/settings/base.py` and `production.py` for all variables.

The entrypoint of the image evaluates `DJANGO_MIGRATE=on` (runs the migrations on start),
`DJANGO_CREATE_SUPERUSER=on` and `DJANGO_LOAD_INITIAL_DATA=on` (only if there are no users yet).

Development
-----------
    python3 -m venv .venv
    .venv/bin/pip install -r requirements/dev.txt
    cd apps
    ../.venv/bin/python manage.py migrate
    ../.venv/bin/python manage.py createsuperuser
    ../.venv/bin/python manage.py runserver

Machine specific settings go into `apps/blogsite/settings/local.py`, which is not in git.

The CSS is built from `apps/static` with gulp (`npm install`, `npx gulp`).

The Python dependencies are listed in `requirements/base.in`. `requirements/base.txt` (installed in the Docker image)
and `requirements/dev.txt` (the same plus the dev tools) are generated from it with pip-tools, with every package
pinned. After changing `base.in`, or to update the packages:

    .venv/bin/pip-compile requirements/base.in      # add --upgrade or --upgrade-package <name>
    .venv/bin/pip-compile requirements/dev.in
    .venv/bin/pip-sync requirements/dev.txt

Release
-------
A release is a git tag `X.Y.Z`. It is created with `git release` (a small release script):

    git release patch        # or minor, major, X.Y.Z

It writes the new version to `apps/blogsite/__init__.py`, commits it as `release X.Y.Z`, creates the
tag and pushes both. The CI checks that the tag matches `__version__` and builds the image
`ghcr.io/g10f/blog-site:X.Y.Z` (and `latest`) natively for amd64 and arm64. A push without a tag does
not start the CI.

Afterwards `git release` runs `./post-release.sh X.Y.Z`, which sets the new version in the theme
repositories checked out next to this one (not committed). Commit them once the CI has built the
image.
