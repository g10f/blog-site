import logging

from django.conf import settings as site_settings

from wagtail.models import Site

log = logging.getLogger(__name__)


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
        'plausible_url': site_settings.PLAUSIBLE_URL,
        'enable_plausible': site_settings.ENABLE_PLAUSIBLE
    }
