import functools

import django_filters
from django.contrib.admin.utils import unquote
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import Http404
from django.urls import URLPattern

from blogsite.base.site import SitePermissionPolicy, get_sites
from wagtail import hooks
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.models import Site
from wagtail.permissions import policy_registry
from wagtail.snippets.views.snippets import SnippetViewSet


def get_site_policy(model):
    """
    The SitePermissionPolicy of a model that belongs to a site. It is registered in wagtail_hooks.py; without one,
    every editor would reach the objects of all sites, so a missing one is an error and not a silent fallback.
    """
    policy = policy_registry.get_by_type(model, fallback=False)
    if not isinstance(policy, SitePermissionPolicy):
        raise ImproperlyConfigured(
            f"{model._meta.label} belongs to a site, but has no SitePermissionPolicy. Register one at the top of "
            f"wagtail_hooks.py with register_permission_policy()."
        )
    return policy


def sites_of_request(request):
    """The sites the filter of a list offers: all for a superuser, otherwise the sites of the user."""
    if request is None:
        return Site.objects.none()
    return Site.objects.filter(pk__in=[site.pk for site in get_sites(request.user)])


def get_site_filter_class(the_model):
    """The filter by site above the list of a snippet, offering only the sites of the user."""

    class SiteFilterSet(WagtailFilterSet):
        site = django_filters.ModelChoiceFilter(queryset=sites_of_request)

        class Meta:
            fields = ["site"]
            model = the_model

    return SiteFilterSet


class SiteScopedChooserViewMixin:
    """For the views of a chooser: only the objects of the sites of the user can be listed and chosen."""

    def get_visible_objects(self, queryset):
        return get_site_policy(self.model_class).visible_to(self.request.user, queryset)

    def get_object_list(self):
        return self.get_visible_objects(super().get_object_list())

    def get_object(self, pk):
        return self.get_visible_objects(self.model_class.objects.all()).get(pk=pk)

    def get_objects(self, pks):
        return self.get_visible_objects(super().get_objects(pks))


def site_scoped_view_class(view_class):
    return type(f"SiteScoped{view_class.__name__}", (SiteScopedChooserViewMixin, view_class), {})


class SiteScopedChooserViewSetMixin:
    """For a ChooserViewSet whose model belongs to a site."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choose_view_class = site_scoped_view_class(self.choose_view_class)
        self.choose_results_view_class = site_scoped_view_class(self.choose_results_view_class)
        self.chosen_view_class = site_scoped_view_class(self.chosen_view_class)
        self.chosen_multiple_view_class = site_scoped_view_class(self.chosen_multiple_view_class)


class SiteScopedViewSetMixin:
    """
    For a SnippetViewSet whose model belongs to a site (several organisations share one blog instance).

    The list shows only the objects of the user's sites. Wagtail's views for a single object (edit, delete, history,
    usage, preview, lock, revisions, ...) each load the object by its id and check only the model permissions, so
    every URL with an object id is wrapped here: an object of another site is answered with 404 before the view
    of Wagtail runs. This way a new view in a later Wagtail version is covered as well.

    The rule itself (which objects a user reaches) is the SitePermissionPolicy of the model, registered in
    wagtail_hooks.py; Wagtail uses it for the bulk actions too.
    """

    def on_register(self):
        # fail at startup, not with an open list, when the policy is missing
        get_site_policy(self.model)
        super().on_register()

    def get_queryset(self, request):
        return get_site_policy(self.model).visible_to(request.user)

    def get_urlpatterns(self):
        return [self.only_objects_of_own_sites(pattern) for pattern in super().get_urlpatterns()]

    def only_objects_of_own_sites(self, pattern):
        if not isinstance(pattern, URLPattern):
            raise ImproperlyConfigured(f"Unexpected URL pattern {pattern!r} in {type(self).__name__}.")
        view = pattern.callback

        @functools.wraps(view)
        def guarded_view(request, *args, **kwargs):
            if "pk" in kwargs:
                visible = get_site_policy(self.model).visible_to(request.user)
                try:
                    found = visible.filter(pk=unquote(str(kwargs["pk"]))).exists()
                except (ValueError, ValidationError):
                    # an id that is not a valid primary key (e.g. letters for a number)
                    found = False
                if not found:
                    raise Http404
            return view(request, *args, **kwargs)

        return URLPattern(pattern.pattern, guarded_view, pattern.default_args, pattern.name)


class SiteFieldChooserViewSet(SiteScopedChooserViewSetMixin, ChooserViewSet):
    # The model can be specified as either the model class or an "app_label.model_name" string;
    # using a string avoids circular imports when accessing the StreamField block class (see below)
    # name = "speaker_chooser"
    url_filter_parameters = ["site"]
    preserve_url_parameters = ["multiple", "site"]


class SiteScopedSnippetChooserViewSet(SiteScopedChooserViewSetMixin, SnippetViewSet.chooser_viewset_class):
    pass


class SiteFieldSnippetViewSet(SiteScopedViewSetMixin, SnippetViewSet):
    """Snippets with a field `site` (People, Speaker, SiteLogo, FooterText, EventTemplate)."""

    filterset_class = None
    chooser_viewset_class = SiteScopedSnippetChooserViewSet

    def __init__(self, **kwargs):
        self.filterset_class = get_site_filter_class(kwargs['model'])
        super().__init__(**kwargs)


@hooks.register("register_admin_viewset")
def register_viewset():
    return SiteFieldChooserViewSet(name="people_chooser", model="base.People")


@hooks.register("register_admin_viewset")
def register_viewset():
    return SiteFieldChooserViewSet(name="speaker_chooser", model="base.Speaker")
