from wagtail import hooks
from wagtail.snippets.models import register_snippet

from blogsite.base.views import SiteFieldSnippetViewSet
from blogsite.blog.admin import EventRegistrationAdmin


@hooks.register("register_admin_viewset")
def register_viewset():
    return EventRegistrationAdmin()


class EventTemplateViewSet(SiteFieldSnippetViewSet):
    icon = "code"
    name = "event-template-view-set"


register_snippet("blogsite.blog.models.EventTemplate", viewset=EventTemplateViewSet)
