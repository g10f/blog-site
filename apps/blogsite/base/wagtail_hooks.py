from blogsite.base.views import SiteFieldSnippetViewSet
from wagtail.snippets.models import register_snippet


class SpeakerViewSet(SiteFieldSnippetViewSet):
    icon = "user"
    name = "speaker-view-set"


class PeopleViewSet(SiteFieldSnippetViewSet):
    icon = "user"
    name = "people-view-set"


class LogoViewSet(SiteFieldSnippetViewSet):
    icon = "image"
    name = "logo-view-set"


class FooterViewSet(SiteFieldSnippetViewSet):
    icon = "code"
    name = "footer-view-set"


register_snippet("blogsite.base.models.Speaker", viewset=SpeakerViewSet)
register_snippet("blogsite.base.models.People", viewset=PeopleViewSet)
register_snippet("blogsite.base.models.SiteLogo", viewset=LogoViewSet)
register_snippet("blogsite.base.models.FooterText", viewset=FooterViewSet)
