from django.db.models import Q
from wagtail.models import Site
from wagtail.permission_policies import ModelPermissionPolicy
from wagtail.permissions import page_permission_policy

# The page permissions that make a site the user's own: he writes for it. Other page permissions (lock, unlock,
# bulk_delete) don't count, they would give access to the people and the registrations of the whole site.
# "add" counts as Wagtail lets a user with only "add" edit his own pages.
SITE_PAGE_PERMISSIONS = {"add_page", "change_page", "publish_page"}

# get_sites() is asked several times in one request (list, each object, filters, forms); like Wagtail's own
# permission cache it is kept on the user object, which lives as long as the request.
SITES_CACHE_ATTRIBUTE = "_blogsite_sites"


def sees_all_sites(user):
    """The one rule for who is not limited to his own sites: active superusers."""
    return user.is_active and user.is_superuser


def get_sites(user):
    """
    The sites of a user: all for a superuser; otherwise the sites in which he may add, change or publish pages,
    either on a page inside the site or on a page above its root page (e.g. the root of the tree for all sites).
    """
    if not hasattr(user, SITES_CACHE_ATTRIBUTE):
        setattr(user, SITES_CACHE_ATTRIBUTE, frozenset(find_sites(user)))
    return getattr(user, SITES_CACHE_ATTRIBUTE)


def find_sites(user):
    if sees_all_sites(user):
        return set(Site.objects.all())
    if not user.is_active:
        return set()
    pages = {permission.page for permission in page_permission_policy.get_cached_permissions_for_user(user)
             if permission.permission.codename in SITE_PAGE_PERMISSIONS}
    sites = set()
    for site in Site.objects.select_related("root_page"):
        for page in pages:
            page_is_in_site = page.path.startswith(site.root_page.path)
            page_is_above_site = site.root_page.path.startswith(page.path)
            if page_is_in_site or page_is_above_site:
                sites.add(site)
    return sites


def pages_of_sites(sites, prefix=""):
    """
    A filter for the pages below the root pages of the given sites. `prefix` is the path to the page field, e.g.
    "event__" for EventRegistration.event.
    """
    condition = Q(pk__in=[])  # matches nothing, for a user without sites
    for site in sites:
        condition |= Q(**{f"{prefix}path__startswith": site.root_page.path})
    return condition


class SitePermissionPolicy(ModelPermissionPolicy):
    """
    The model permissions of Django (add, change, delete, ...), and on top of them: a user who is not a superuser
    only reaches the objects of his own sites, the sites of the pages he may edit (get_sites). Several
    organisations share one blog instance, and an editor must not see or change what belongs to another one.

    Wagtail uses this policy for the snippet lists, the bulk actions and some single views; SiteScopedViewSetMixin
    (views.py) uses visible_to() for all other views that take an object id.

    Objects without a site (site is empty) are only reached by superusers.
    """

    def filter_by_sites(self, queryset, sites):
        """The objects of the given sites. Override for a model whose site is not in a field `site`."""
        return queryset.filter(site__in=sites)

    def visible_to(self, user, queryset=None):
        if queryset is None:
            queryset = self.model._default_manager.all()
        if sees_all_sites(user):
            return queryset
        return self.filter_by_sites(queryset, get_sites(user))

    def user_has_permission_for_instance(self, user, action, instance):
        if not super().user_has_permission_for_instance(user, action, instance):
            return False
        return self.visible_to(user).filter(pk=instance.pk).exists()

    def instances_user_has_any_permission_for(self, user, actions):
        return self.visible_to(user, super().instances_user_has_any_permission_for(user, actions))


class EventPageSitePermissionPolicy(SitePermissionPolicy):
    """For models that belong to a site through their event page (EventRegistration.event)."""

    def filter_by_sites(self, queryset, sites):
        return queryset.filter(pages_of_sites(sites, prefix="event__"))
