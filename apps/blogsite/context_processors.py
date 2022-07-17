import logging

from django.conf import settings as site_settings

from wagtail.models import Site

log = logging.getLogger(__name__)


def settings(request):
    site = Site.find_for_request(request=request)
    return {
        'site': site,
        'wagtail_site_name':  site.site_name if site.site_name else site_settings.WAGTAIL_SITE_NAME,
    }
