import logging

from django.conf import settings as site_settings

log = logging.getLogger(__name__)


def settings(request):
    return {
        'wagtail_site_name': site_settings.WAGTAIL_SITE_NAME,
    }
