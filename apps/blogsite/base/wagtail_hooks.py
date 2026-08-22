from django.urls import reverse_lazy

from blogsite.base.views import SiteFieldSnippetViewSet
from draftjs_exporter.dom import DOM
from wagtail import hooks
from wagtail.admin.rich_text.converters.contentstate import link_entity
from wagtail.admin.rich_text.converters.html_to_contentstate import (
    ExternalLinkElementHandler,
    PageLinkElementHandler,
)
from wagtail.admin.rich_text.editors.draftail import features as draftail_features
from wagtail.rich_text import LinkHandler
from wagtail.snippets.models import register_snippet
from wagtail.whitelist import check_url


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


class ButtonLinkHandler(LinkHandler):
    identifier = 'button'

    @classmethod
    def expand_db_attributes(cls, attrs):
        id_ = attrs.get('id')
        if id_ is not None:
            try:
                from wagtail.models import Page
                page = Page.objects.get(pk=id_).specific
                href = page.full_url
            except Exception:
                href = '#'
        else:
            href = attrs.get('href', '')
        return f'<a href="{href}" class="btn btn-primary">'


def button_link_entity(props):
    id_ = props.get('id')
    link_props = {'linktype': 'button'}
    if id_ is not None:
        link_props['id'] = id_
    else:
        link_props['href'] = check_url(props.get('url', ''))
    return DOM.create_element('a', link_props, props['children'])


@hooks.register('register_rich_text_features')
def register_button_link_feature(features):
    feature_name = 'button-link'
    type_ = 'BUTTON_LINK'

    features.register_link_type(ButtonLinkHandler)

    features.register_editor_plugin(
        'draftail', feature_name,
        draftail_features.EntityFeature(
            {
                'type': type_,
                'icon': 'link',
                'description': 'Button',
                'attributes': ['url', 'id', 'parentId'],
                'allowlist': {
                    'href': '^(http:|https:|mailto:|#|undefined$)',
                },
                'chooserUrls': {
                    'pageChooser': reverse_lazy('wagtailadmin_choose_page'),
                    'externalLinkChooser': reverse_lazy('wagtailadmin_choose_page_external_link'),
                    'emailLinkChooser': reverse_lazy('wagtailadmin_choose_page_email_link'),
                    'phoneLinkChooser': reverse_lazy('wagtailadmin_choose_page_phone_link'),
                    'anchorLinkChooser': reverse_lazy('wagtailadmin_choose_page_anchor_link'),
                },
            },
            js=['wagtailadmin/js/page-chooser-modal.js'],
        )
    )

    features.register_converter_rule('contentstate', feature_name, {
        'from_database_format': {
            'a[linktype="button"][href]': ExternalLinkElementHandler(type_),
            'a[linktype="button"][id]': PageLinkElementHandler(type_),
        },
        'to_database_format': {
            'entity_decorators': {type_: button_link_entity}
        }
    })
