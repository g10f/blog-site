import logging
from functools import cache
from importlib import import_module

from django.conf import settings as site_settings

from wagtail.models import Site

from blogsite import __version__

log = logging.getLogger(__name__)


@cache
def site_version():
    """The version of the deployed image, shown in the footer.

    A theme image (FROM this image) names its package in the setting THEME; its __version__ is the
    version of the theme release (X.Y.Z, or X.Y.Z.N for a change of the theme alone). Without a theme,
    or a theme without __version__, it is the version of this project.
    """
    theme = getattr(site_settings, 'THEME', None)
    if theme:
        theme_version = getattr(import_module(theme), '__version__', None)
        if theme_version:
            return theme_version
    return __version__


def settings(request):
    site = Site.find_for_request(request=request)
    return {
        'site': site,
        'wagtail_site_name':  site.site_name if site and site.site_name else site_settings.WAGTAIL_SITE_NAME,
        'wagtail_i18n_enabled': site_settings.WAGTAIL_I18N_ENABLED,
        'logo_size': site_settings.LOGO_SIZE,
        'hero_with_title': site_settings.HERO_WITH_TITLE,
        'event_registration_email': site_settings.EVENT_REGISTRATION_EMAIL,
        'event_registration_phone_number': site_settings.EVENT_REGISTRATION_PHONE_NUMBER,
        'enable_plausible': site_settings.ENABLE_PLAUSIBLE,
        'version': site_version(),
    }
