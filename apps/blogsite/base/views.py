from blogsite.base.site import get_sites
from wagtail import hooks
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.snippets.views.snippets import SnippetViewSet


def get_site_filter_class(the_model):
    """
    Create site filter class for model
    :param the_model:
    :return:
    """
    class SiteFilterSet(WagtailFilterSet):
        class Meta:
            fields = ["site"]
            model = the_model

        def filter_queryset(self, queryset):
            return super().filter_queryset(queryset)

    return SiteFilterSet


class SiteFieldSnippetViewSet(SnippetViewSet):
    filterset_class = None

    def get_queryset(self, request):
        sites = get_sites(request.user)
        queryset = self.model._default_manager.all()
        if request.user.is_superuser:
            return queryset
        else:
            return queryset.filter(site__in=sites)

    def __init__(self, **kwargs):
        self.filterset_class = get_site_filter_class(kwargs['model'])
        super().__init__(**kwargs)


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
