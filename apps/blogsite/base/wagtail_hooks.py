from blogsite.base.views import SiteFieldSnippetViewSet
from wagtail.snippets.models import register_snippet


class SpeakerViewSet(SiteFieldSnippetViewSet):
    name = "speaker-view-set"


class PeopleViewSet(SiteFieldSnippetViewSet):
    name = "people-view-set"


class LogoViewSet(SiteFieldSnippetViewSet):
    name = "logo-view-set"


class FooterViewSet(SiteFieldSnippetViewSet):
    name = "footer-view-set"


register_snippet("blogsite.base.models.Speaker", viewset=SpeakerViewSet)
register_snippet("blogsite.base.models.People", viewset=PeopleViewSet)
register_snippet("blogsite.base.models.SiteLogo", viewset=LogoViewSet)
register_snippet("blogsite.base.models.FooterText", viewset=FooterViewSet)
