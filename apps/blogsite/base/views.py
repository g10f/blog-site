from blogsite.base.forms import SiteFieldForm
from blogsite.base.site import get_sites
from wagtail import hooks
from wagtail.admin.panels import get_form_for_model
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.snippets.views.snippets import SnippetViewSet


class SiteFieldSnippetViewSet(SnippetViewSet):
    icon = "user"

    def get_queryset(self, request):
        sites = get_sites(request.user)
        queryset = self.model._default_manager.all()
        if request.user.is_superuser:
            return queryset
        else:
            return queryset.filter(site__in=sites)


class SiteFieldChooserViewSet(ChooserViewSet):
    # The model can be specified as either the model class or an "app_label.model_name" string;
    # using a string avoids circular imports when accessing the StreamField block class (see below)
    # name = "speaker_chooser"
    url_filter_parameters = ["site"]
    preserve_url_parameters = ["multiple", "site"]


@hooks.register("register_admin_viewset")
def register_viewset():
    return SiteFieldChooserViewSet(name="people_chooser", model="base.People")


@hooks.register("register_admin_viewset")
def register_viewset():
    return SiteFieldChooserViewSet(name="speaker_chooser", model="base.Speaker")
