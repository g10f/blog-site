from wagtail import hooks
from wagtail.permissions import register_permission_policy
from wagtail.snippets.models import register_snippet

from blogsite.base.site import EventPageSitePermissionPolicy, SitePermissionPolicy
from blogsite.base.views import SiteFieldSnippetViewSet
from blogsite.blog.admin import EventRegistrationAdmin
from blogsite.blog.models import EventRegistration, EventTemplate

# Registered before the viewsets below, as Wagtail requires; see SitePermissionPolicy.
register_permission_policy(EventTemplate, SitePermissionPolicy(EventTemplate), exact_class=True)
register_permission_policy(EventRegistration, EventPageSitePermissionPolicy(EventRegistration), exact_class=True)


@hooks.register("register_admin_viewset")
def register_viewset():
    return EventRegistrationAdmin()


class EventTemplateViewSet(SiteFieldSnippetViewSet):
    icon = "code"
    name = "event-template-view-set"


register_snippet("blogsite.blog.models.EventTemplate", viewset=EventTemplateViewSet)
