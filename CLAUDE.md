# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Django + Wagtail CMS for multi-site blogs with events ("The Blog Site" / `g10f/blog-site`), multi-language
(en/de/pl, default `de`), optional OIDC login for the admin, and optional Campai event-booking integration.
Deployed as a Docker image behind a Varnish cache.

**This repo is a base image for theme repos.** The sibling checkouts `../blog-doreen-theme`, `../blog-michal-theme`
and `../afd-blog` each build `FROM ghcr.io/g10f/blog-site:<version>`, add a small Django app (e.g. `doreen_theme`)
and set `THEME=<app>`. Keep that in mind when changing templates, template block names, context variables or
shared SCSS; themes may override or import them (see "Themes" below).

## Repo layout

- `apps/`: the Django project root (`manage.py` lives here). `DJANGO_SETTINGS_MODULE` defaults to
  `blogsite.settings.dev` locally and `blogsite.settings.production` in Docker.
  - `apps/blogsite/`: project package (settings, urls, wsgi, `context_processors.py`, `templates/`, `locale/`,
    pagination template tag). It is itself an installed app, so its `templates/` and `locale/` are picked up.
    - `base/`: shared models and admin plumbing: `People`, `Speaker`, `SiteLogo` and `FooterText` snippets,
      `HomePage`, `StandardPage`, `TwoColumnsPage`, `PersonsPage`, `FormPage`, `TwoColumnsFormPage`,
      `SocialMediaSettings`, stream field blocks (`blocks.py`), image formats, navigation/gallery template tags,
      and the site-scoped snippet/chooser viewsets (`views.py`, `site.py`, `forms.py`).
    - `blog/`: `BlogPage`, `EventPage`, `BlogIndexPage`, `EventIndexPage`, `EventTemplate` snippet,
      `EventRegistration` (+ admin viewset with CSV export), and the Campai sync.
    - `search/`: a single view using Wagtail's database search backend.
  - `apps/oidc/`: `mozilla-django-oidc` integration: auth backend mapping OIDC `roles` claims to Django groups via
    `RoleGroup`, `UserProfile` (stores the OIDC `sub`), and admin login/logout views.
  - `apps/core/`: `PathBasedCsrfViewMiddleware` and a small `update_url` helper.
  - `apps/templates/`: project-level template overrides (currently the Wagtail admin login page).
  - `apps/static/`: source SCSS/JS (Bootstrap 5 + Bootstrap Icons + custom SCSS), compiled by gulp into
    `apps/static/css`; vendor JS goes to `apps/static/js/vendor`. `apps/static/root/` holds `robots.txt`/`favicon.ico`,
    which WhiteNoise serves at the URL root (`WHITENOISE_ROOT`).
- `htdocs/`: default `STATIC_ROOT`/`MEDIA_ROOT` (gitignored).
- `data/`: default dev sqlite DB `data/blogsite.db` (gitignored).
- `demo-data/`: a leftover art-site dataset; no blog-site setting references it.
- `requirements/base.txt` (referenced by the root `requirements.txt`): Python dependencies, with Django and Wagtail pinned.

## Settings

- `settings/base.py`: all shared config, driven by env vars. It also sets `DEBUG=True` automatically when
  invoked as `manage.py runserver` or `test`.
- `settings/dev.py`: `DEBUG=True`, `ALLOWED_HOSTS=['*']`, console email backend, then `from .local import *` if present.
- `settings/production.py`: reads `THEME`, `ALLOWED_HOSTS`, `DEBUG` and the `OIDC_*` endpoints/client from the
  environment, then also imports `local.py` if present.
- `settings/local.py` is **gitignored** and machine-specific. It typically selects a local Postgres DB, a `THEME`,
  media root and real OIDC/Campai credentials. Never commit it or copy values out of it.

Key env vars: `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `THEME`, `LANGUAGE_CODE`, `WAGTAIL_SITE_NAME`,
`WAGTAIL_I18N_ENABLED`, `WAGTAILADMIN_BASE_URL`, `WAGTAILFRONTENDCACHE_LOCATION` (Varnish), `BLOGSITE_PAGE_SIZE`,
`RECAPTCHA_PUBLIC_KEY`/`RECAPTCHA_PRIVATE_KEY`, `EMAIL_HOST`/`EMAIL_PORT`, `DEFAULT_FROM_EMAIL`,
`EVENT_REGISTRATION_EMAIL`, `ADMINS` (`Name,email;Name,email`), `EMAIL_SUBJECT_PREFIX`, `LOGO_SIZE`,
`HERO_WITH_TITLE`, `ENABLE_PLAUSIBLE`/`PLAUSIBLE_URL`, `CAMPAI_BASE_URL`/`CAMPAI_API_URL`/`CAMPAI_API_KEY`,
`OIDC_OP_NAME` + `OIDC_OP_*_ENDPOINT`/`OIDC_OP_LOGOUT_URL_METHOD`/`OIDC_RP_CLIENT_ID`/`OIDC_RP_CLIENT_SECRET`,
`MEDIA_URL`, `STATIC_ROOT`, `MEDIA_ROOT`.

Several of these (`LOGO_SIZE`, `HERO_WITH_TITLE`, `ENABLE_PLAUSIBLE`, event registration email/phone, site name)
reach templates through `blogsite.context_processors.settings`.

## Common commands

Run Django management commands from `apps/`:

```bash
cd apps
python manage.py runserver          # uses blogsite.settings.dev (+ local.py if present)
python manage.py migrate
python manage.py makemigrations
python manage.py createsuperuser
python manage.py collectstatic
python manage.py makemessages -l de  # then compilemessages; locale files live in blogsite/locale
python manage.py sync_campai_events  # pull events from Campai (needs CAMPAI_* settings)
python manage.py user_count          # used by docker-entrypoint.sh
```

There is no automated test suite, and there is no linter config.

Frontend assets are built with gulp from the repo root:

```bash
npm install
npx gulp          # apps/static/scss/main.scss -> apps/static/css/main(.min).css, copies vendor JS + icon fonts
```

There is no `watch` task. Compiled CSS is committed, so rebuild it and commit it with SCSS changes.

Docker / release:

```bash
./build-and-push.sh   # local buildx build tagged ghcr.io/g10f/blog-site:<__version__> (uses --load, doesn't push)
./set-version.sh      # edit VERSION in the script first; bumps apps/blogsite/__init__.py AND the FROM tag +
                      # __version__ in ../blog-michal-theme, ../afd-blog and ../blog-doreen-theme
```

CI (`.github/workflows/ci.yaml`) builds and pushes a multi-arch image to `ghcr.io/g10f/blog-site` on every push
to `main`, tagged with `latest`, the version from `apps/version.py` and the commit SHA. The version bump is the
release mechanism. The image's entrypoint `apps/docker-entrypoint.sh` optionally runs `migrate` / `createsuperuser` /
`loaddata dummy-data` depending on `DJANGO_MIGRATE`, `DJANGO_CREATE_SUPERUSER` and `DJANGO_LOAD_INITIAL_DATA`.
Note that no `dummy-data` fixture currently exists in the repo.

## Architecture notes

- **Themes.** `THEME` is prepended to `INSTALLED_APPS` (in `production.py`, and usually in `local.py`). Templates are
  resolved by the filesystem loader (`apps/templates`) first, then the app-directories loader
  in `INSTALLED_APPS` order. A theme app's `templates/` therefore overrides `blogsite/templates/`. Static files also
  resolve theme-first, because `AppDirectoriesFinder` comes before `FileSystemFinder`, so a theme's `static/css/main.css`
  replaces the base one. Theme SCSS imports `apps/static/scss/mixins/_forms.scss` and
  `apps/static/scss/forms/_validation.scss` from `../blog-site` by relative path. Renaming or moving those breaks theme builds.
- **Multi-site admin scoping.** One instance serves several Wagtail `Site`s. The snippets `People`, `Speaker`,
  `SiteLogo`, `FooterText` and `EventTemplate` each carry a `site` FK and use `SiteFieldForm` (restricts the `site`
  choices) plus `SiteFieldSnippetViewSet`, which filters listings to the sites the user can explore
  (`base/site.py:get_sites`). Superusers see everything. Author/speaker choosers on pages are `SiteFieldChooserViewSet`
  widgets linked to `#id_site`. Follow the same pattern for any new per-site snippet.
- **Page types.** `EventPage` subclasses `BlogPage` (multi-table inheritance). `EventIndexPage` subclasses
  `BlogIndexPage` and overrides `get_posts`/`get_years`/`children` to order by `start_date`. `BlogIndexPage` is a
  `RoutablePageMixin` page with a `tags/<tag>/` sub-view and a `?year=` filter. `BlogPage` keeps the `?tag=` filter
  for next/previous navigation. An `EventPage` can inherit content and tags from an `EventTemplate` snippet.
  `People` are blog authors and `Speaker`s are event speakers, each linked through an `Orderable` relationship model.
- **Event registration** is a `serve()` override on `EventPage`, not Wagtail's form flow. POST builds an
  `EventRegistration` via `EventRegistrationForm` (ReCaptcha, sends mail with optional CC to the registrant), then
  redirects with `?landing=1` to show the thank-you text. Registration is blocked when the event is expired, closed,
  booked up, or has `with_registration_form=False`. `FormPage`/`TwoColumnsFormPage` go through `CustomFormBuilder`
  instead. It injects a ReCaptcha field and a honeypot field (`h_message`, non-empty means the submission is silently
  dropped as spam) and adds Bootstrap's `form-control` to every widget.
- **Campai integration.** `EventPage.campai_event_id` links a page to a Campai booking event.
  `update_or_create_event_from_campai()` (in `blog/models.py`) maps Campai data onto the page (title, dates, prices
  "Standard"/"Mitglieder", speakers from `Dozent:` categories matched by `Speaker.slug`, location from the `Ort:`
  category, Markdown details into the body) and publishes a revision only when fields changed. New events are added
  under the *first* `EventIndexPage`. `EventPage.serve()` calls the Campai API on every request for linked events.
  `sync_campai_events` also deletes future events that have disappeared from Campai. Its scheduling is external to this repo.
- **Frontend cache purging is signal-driven.** `blog/models.py` connects `page_published`, `pre_delete` and
  `post_page_move` to `blog_page_changed()`, which purges every live `BlogIndexPage` containing the post, plus any
  `HomePage` featuring that index via `featured_section_1`/`featured_section_2`, in one `PurgeBatch`.
  `BlogIndexPage.get_cached_paths()` uses `base.models.get_cached_path()` to enumerate every tag/page-number URL
  variant. Extend it whenever you add a new filter dimension to an index page.
- **OIDC admin login** is only wired into `urls.py` when `OIDC_OP_NAME` is set. It then replaces Wagtail's
  `admin/login/` (which auto-redirects to the provider; `?noredir=1` shows the local login form) and `admin/logout/`
  (RP-initiated logout with `id_token_hint`). `oidc.backend.AuthenticationBackend` rejects users whose `roles` claim
  matches no `RoleGroup`. It takes the username from the `name` claim and syncs groups, `is_staff` and
  `is_superuser` from `RoleGroup` on every login.
- **Rich text / images.** `base/wagtail_hooks.py` registers a custom Draftail `button-link` feature (entity
  `BUTTON_LINK`, link type `button`, rendered as `<a class="btn btn-primary">`). Enable it per field via
  `features=[..., 'button-link']` (see `HomePage.promo_text`). A custom entity type needs two things Wagtail won't warn
  about. First, an editor plugin, `apps/static/js/draftail-button-link.js`, registered with
  `window.draftail.registerPlugin`; without it the toolbar button does nothing. Second, `from_database_format`
  selectors with a single condition. `HTMLRuleset` silently ignores combined selectors like `a[x][y]`, and rules of
  equal priority clash with the core `a[href]` link rule. That's why external buttons are stored as
  `<a linktype="button" url="...">`, not with `href`. `base/image_formats.py` replaces Wagtail's `fullwidth`/`left`/`right` rich-text image
  formats with Bootstrap-classed versions.
- **Translation.** The snippets use `TranslatableMixin`, and pages use Wagtail's built-in translation plus
  `wagtail.contrib.simple_translation`. `People.copy_for_translation()` and `Speaker.copy_for_translation()` exclude
  `index_entries` to work around a copy failure. URLs are `i18n_patterns` with `prefix_default_language=False` when
  `WAGTAIL_I18N_ENABLED`.
- **CSRF is opt-in per path.** `core.middleware.PathBasedCsrfViewMiddleware` only enforces CSRF under
  `CSRF_REQUIRED_PATHS` (`/login`, `/admin`, `/django-admin`), so public pages can be edge-cached. New authenticated
  views must live under one of these prefixes, or you must add a prefix. The public event-registration and form
  POSTs rely on ReCaptcha, not CSRF.
