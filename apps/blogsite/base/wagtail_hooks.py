from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _

from blogsite.base.models import FooterText, People, SiteLogo, Speaker
from blogsite.base.site import SitePermissionPolicy
from blogsite.base.views import SiteFieldSnippetViewSet
from draftjs_exporter.dom import DOM
from wagtail import hooks
from wagtail.admin.rich_text.converters.html_to_contentstate import PageLinkElementHandler
from wagtail.admin.rich_text.editors.draftail import features as draftail_features
from wagtail.models import Page
from wagtail.permissions import register_permission_policy
from wagtail.rich_text import LinkHandler
from wagtail.rich_text.pages import PageLinkHandler
from wagtail.snippets.models import register_snippet
from wagtail.whitelist import check_url

# The snippets that belong to a site: an editor only reaches those of his own sites (see SitePermissionPolicy).
# Registered before the viewsets below, as Wagtail requires.
for site_model in (People, Speaker, SiteLogo, FooterText):
    register_permission_policy(site_model, SitePermissionPolicy(site_model), exact_class=True)


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
        return cls.expand_db_attributes_many([attrs])[0]

    @classmethod
    def expand_db_attributes_many(cls, attrs_list):
        # page buttons are rendered like normal page links (bulk query, localized url), external ones use their url
        page_tags = iter(PageLinkHandler.expand_db_attributes_many([attrs for attrs in attrs_list if 'id' in attrs]))
        tags = [next(page_tags) if 'id' in attrs else '<a href="%s">' % escape(attrs.get('url', '')) for attrs in attrs_list]
        return [tag.replace('<a', '<a class="btn btn-primary"', 1) for tag in tags]

    @classmethod
    def extract_references(cls, attrs):
        if 'id' in attrs:
            yield from PageLinkHandler.extract_references(attrs)


class ButtonLinkElementHandler(PageLinkElementHandler):
    def get_attribute_data(self, attrs):
        if 'id' in attrs:
            return super().get_attribute_data(attrs)
        return {'url': attrs.get('url')}


def button_link_entity(props):
    # External buttons store their target in `url`, not `href`: HTMLRuleset doesn't support combined selectors,
    # so <a linktype="button" href="..."> would also match the core link rule 'a[href]' and load as a plain link.
    id_ = props.get('id')
    link_props = {'linktype': 'button'}
    if id_ is not None:
        link_props['id'] = id_
    else:
        link_props['url'] = check_url(props.get('url', ''))
    return DOM.create_element('a', link_props, props['children'])


@hooks.register('register_icons')
def register_icons(icons):
    # used by the button-link toolbar button, Wagtail has no icon that looks like a button
    return icons + ['blogsite/icons/hand-index.svg']


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
                'icon': 'hand-index',
                'description': _('Link Button'),
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
            js=['wagtailadmin/js/page-chooser-modal.js', 'js/draftail-button-link.js'],
        )
    )

    features.register_converter_rule('contentstate', feature_name, {
        'from_database_format': {
            'a[linktype="button"]': ButtonLinkElementHandler(type_),
        },
        'to_database_format': {
            'entity_decorators': {type_: button_link_entity}
        }
    })


# Editors may change and publish every page of their site (blogsite/base/editors.py), and Wagtail ties deleting
# and unpublishing to these rights. So deleting and unpublishing follow the right to add instead: whoever may not
# add a page at its place may not remove it either. An editor who may add only blog posts can delete a blog post
# but not the imprint, which he couldn't add again; an advanced editor can; and as nobody but a superuser may add
# pages at the top of the tree, only a superuser can take the home page of a site (and with it the site) offline.
# Groups that may add pages everywhere (e.g. the editors of the other blog instances) keep all their rights.
STRUCTURE_PAGE_MESSAGE = _("You can't delete or unpublish the page “%(title)s”, as you may not add pages at its "
                           "place. Please contact the operator of the website.")


def may_add_at_place_of(user, page):
    parent = page.get_parent()
    return parent is not None and parent.permissions_for_user(user).can_add_subpage()


def refuse_unless_may_add_at_place(request, pages):
    if request.user.is_superuser:
        return None
    for page in pages:
        if not may_add_at_place_of(request.user, page):
            messages.error(request, STRUCTURE_PAGE_MESSAGE % {"title": page.get_admin_display_title()})
            parent = page.get_parent()
            if parent is None:
                return redirect("wagtailadmin_home")
            return redirect("wagtailadmin_explore", parent.pk)
    return None


@hooks.register("before_delete_page")
def only_deleted_where_may_add(request, page):
    return refuse_unless_may_add_at_place(request, [page])


@hooks.register("before_unpublish_page")
def only_unpublished_where_may_add(request, page):
    return refuse_unless_may_add_at_place(request, [page])


@hooks.register("before_bulk_action")
def only_removed_in_bulk_where_may_add(request, action_type, objects, action_class_instance):
    if action_type in ("delete", "unpublish") and all(isinstance(obj, Page) for obj in objects):
        return refuse_unless_may_add_at_place(request, objects)
    return None
