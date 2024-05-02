import logging

from blogsite.base.site import get_sites
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.models import Site

logger = logging.getLogger(__name__)


class SiteFieldForm(WagtailAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'site' in self.fields and 'for_user' in kwargs:
            sites = get_sites(kwargs['for_user'])
            self.fields['site'].queryset = Site.objects.filter(pk__in=[site.pk for site in sites])
        else:
            if 'site' not in self.fields:
                logger.warning('No site field in form selected')
            if 'for_user' not in kwargs:
                logger.warning('No for_user kwargs')

    class Meta:
        # TODO: use fields defined in panel
        exclude = ()
