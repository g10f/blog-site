"""
Separation by site: several organisations share one blog instance, each with its own site. An editor of one site
must not see, open, change, delete or export what belongs to another site.

Every model with data of a site has a test here. A new model that belongs to a site has to be added to
SITE_SCOPED (with a SitePermissionPolicy in wagtail_hooks.py) or, with a reason, to one of the other lists;
ModelListTest fails until that is done.
"""
import shutil
import tempfile

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.images.models import Image
from wagtail.images.tests.utils import get_test_image_file
from wagtail.models import GroupPagePermission, Page, Site
from wagtail.permissions import policy_registry

from blogsite.base.models import FooterText, FormField, People, SiteLogo, SiteSettings, Speaker
from blogsite.base.site import SitePermissionPolicy, get_sites
from blogsite.blog.models import (BlogPageTag, BlogPeopleRelationship, EventDate, EventIndexPage, EventPage,
                                  EventRegistration, EventSpeakerRelationship, EventTemplate, EventTemplateTag)
from oidc.models import RoleGroup, UserProfile

User = get_user_model()

# models whose objects belong to one site; an editor only reaches those of his own sites
SITE_SCOPED = [People, Speaker, SiteLogo, FooterText, EventTemplate, EventRegistration]

# models that belong to a site, but are not separated yet (next steps of the separation by site)
NOT_SEPARATED_YET = {
    SiteSettings: "Wagtail's settings view; an editor with the permission can open the settings of every site",
}

# parts of a page or a snippet, only edited inside it: they are protected with the page or snippet they belong to
PART_OF_ANOTHER_OBJECT = [FormField, BlogPeopleRelationship, EventSpeakerRelationship, BlogPageTag, EventTemplateTag,
                          EventDate]

# shared on purpose by the whole instance, only edited by superusers in the Django admin
INSTANCE_WIDE = [RoleGroup, UserProfile]

# views that answer an existing own object with something else than 200/302: unpublish needs a live object,
# unschedule a scheduled revision
OWN_OBJECT_NOT_OPENED = {"unpublish", "revisions_unschedule"}


class ModelListTest(TestCase):
    def project_models(self):
        return [model for model in apps.get_models()
                if model.__module__.startswith(("blogsite.", "oidc.", "core."))
                and not issubclass(model, Page)]

    def test_every_model_is_in_one_of_the_lists(self):
        listed = SITE_SCOPED + list(NOT_SEPARATED_YET) + PART_OF_ANOTHER_OBJECT + INSTANCE_WIDE
        for model in self.project_models():
            with self.subTest(model=model._meta.label):
                self.assertEqual(listed.count(model), 1, "the model has to be in exactly one list of this file")

    def test_every_model_with_a_site_is_separated_or_known_to_be_open(self):
        for model in self.project_models():
            site_fields = [field for field in model._meta.get_fields()
                           if field.concrete and field.is_relation and field.related_model is Site]
            if site_fields:
                with self.subTest(model=model._meta.label):
                    self.assertIn(model, SITE_SCOPED + list(NOT_SEPARATED_YET))

    def test_site_scoped_models_have_the_site_policy(self):
        for model in SITE_SCOPED:
            with self.subTest(model=model._meta.label):
                self.assertIsInstance(policy_registry.get_by_type(model, fallback=False), SitePermissionPolicy)


class TwoSitesMixin:
    """Two sites, A and B, each with an editor who may edit the pages of his site and use all snippets."""

    @classmethod
    def setUpClass(cls):
        cls.media_root = tempfile.mkdtemp()
        cls.media_settings = override_settings(MEDIA_ROOT=cls.media_root)
        cls.media_settings.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_settings.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        root = Page.get_first_root_node()
        image = Image.objects.create(title="logo", file=get_test_image_file())
        cls.objects = {}
        cls.editors = {}
        cls.events = {}
        for name in ("a", "b"):
            home = root.add_child(instance=Page(title=f"Home {name}", slug=f"home-{name}"))
            site = Site.objects.create(hostname=f"{name}.example.com", root_page=home, site_name=f"Site {name}")
            event_index = home.add_child(instance=EventIndexPage(title=f"Events {name}", slug=f"events-{name}"))
            event = event_index.add_child(instance=EventPage(title=f"Event {name}", slug=f"event-{name}"))
            cls.events[name] = event

            cls.objects[name] = {
                People: People.objects.create(site=site, first_name="Anna", last_name=name, slug=f"anna-{name}"),
                Speaker: Speaker.objects.create(site=site, first_name="Bert", last_name=name, slug=f"bert-{name}"),
                SiteLogo: SiteLogo.objects.create(site=site, image_header=image, image_footer=image, image_ico=image),
                FooterText: FooterText.objects.create(site=site, body=f"footer {name}"),
                EventTemplate: EventTemplate.objects.create(site=site, name=f"template {name}"),
                EventRegistration: EventRegistration.objects.create(
                    event=event, subject="registration", name=f"Carla {name}", email=f"carla-{name}@example.com",
                    telephone="0123", message="hello", to_email="office@example.com", is_member=True),
            }
            # a revision for the history views of the snippets that have revisions
            for model in (SiteLogo, FooterText):
                cls.objects[name][model].save_revision()

            group = Group.objects.create(name=f"Editors {name}")
            group.permissions.add(Permission.objects.get(content_type__app_label="wagtailadmin",
                                                         codename="access_admin"))
            for model in SITE_SCOPED:
                group.permissions.add(*Permission.objects.filter(
                    content_type=ContentType.objects.get_for_model(model)))
            for codename in ("add_page", "change_page", "publish_page"):
                GroupPagePermission.objects.create(group=group, page=home, permission=Permission.objects.get(
                    content_type__app_label="wagtailcore", codename=codename))
            editor = User.objects.create_user(f"editor-{name}", password="x")
            editor.groups.add(group)
            cls.editors[name] = editor

        # registration of a deleted event: it belongs to no site any more
        cls.orphan = EventRegistration.objects.create(event=None, subject="registration", name="Dora",
                                                      email="dora@example.com", message="hi", to_email="o@example.com")
        cls.superuser = User.objects.create_superuser("admin", password="x")

    def viewset(self, model):
        return model.snippet_viewset

    def url(self, model, name, *args):
        return reverse(self.viewset(model).get_url_name(name), args=args)


class SnippetSeparationTest(TwoSitesMixin, TestCase):
    def setUp(self):
        self.client.force_login(self.editors["a"])

    def object_urls(self, model, obj):
        """All URLs of the viewset that take the id of an object, the revision views included."""
        revision = getattr(obj, "latest_revision", None)
        values = {"pk": obj.pk, "revision_id": revision.pk if revision else None,
                  "revision_id_a": "earliest", "revision_id_b": "latest"}
        for pattern in self.viewset(model).get_urlpatterns():
            arguments = set(pattern.pattern.regex.groupindex)
            if "pk" in arguments:
                with self.subTest(model=model._meta.label, view=pattern.name):
                    self.assertTrue(arguments <= set(values), f"unknown URL arguments {arguments}")
                kwargs = {argument: values.get(argument) for argument in arguments}
                if None not in kwargs.values():
                    yield pattern.name, reverse(self.viewset(model).get_url_name(pattern.name), kwargs=kwargs)

    def test_revision_views_are_tested(self):
        names = {name for name, url in self.object_urls(FooterText, self.objects["b"][FooterText])}
        self.assertTrue({"revisions_view", "revisions_revert", "revisions_compare"} <= names)

    def test_list_shows_only_own_objects(self):
        for model in SITE_SCOPED:
            with self.subTest(model=model._meta.label):
                response = self.client.get(self.url(model, "list"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, self.url(model, "edit", self.objects["a"][model].pk))
                self.assertNotContains(response, self.url(model, "edit", self.objects["b"][model].pk))

    def test_objects_of_another_site_are_not_found(self):
        for model in SITE_SCOPED:
            for name, url in self.object_urls(model, self.objects["b"][model]):
                with self.subTest(model=model._meta.label, view=name):
                    self.assertEqual(self.client.get(url).status_code, 404)

    def test_own_objects_can_be_opened(self):
        # the same URLs as above, so that the 404 really comes from the site and not from a broken URL
        for model in SITE_SCOPED:
            for name, url in self.object_urls(model, self.objects["a"][model]):
                if name in OWN_OBJECT_NOT_OPENED:
                    continue
                with self.subTest(model=model._meta.label, view=name):
                    self.assertIn(self.client.get(url).status_code, (200, 302))

    def test_objects_of_another_site_can_not_be_changed_or_deleted(self):
        for model in SITE_SCOPED:
            obj = self.objects["b"][model]
            with self.subTest(model=model._meta.label):
                self.assertEqual(self.client.post(self.url(model, "edit", obj.pk), {}).status_code, 404)
                self.assertEqual(self.client.post(self.url(model, "delete", obj.pk)).status_code, 404)
                self.assertTrue(model.objects.filter(pk=obj.pk).exists())

    def test_bulk_delete_leaves_objects_of_another_site(self):
        for model in SITE_SCOPED:
            obj = self.objects["b"][model]
            meta = model._meta
            url = reverse("wagtail_bulk_action", args=(meta.app_label, meta.model_name, "delete"))
            with self.subTest(model=meta.label):
                self.client.post(f"{url}?id={obj.pk}")
                self.assertTrue(model.objects.filter(pk=obj.pk).exists())

    def test_export_contains_only_own_registrations(self):
        response = self.client.get(self.url(EventRegistration, "list") + "?export=csv")
        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content).decode() if response.streaming else response.content.decode()
        self.assertIn("carla-a@example.com", content)
        self.assertNotIn("carla-b@example.com", content)
        self.assertNotIn("dora@example.com", content)

    def test_registration_filter_offers_only_own_events(self):
        response = self.client.get(self.url(EventRegistration, "list"))
        self.assertContains(response, "Event a")
        self.assertNotContains(response, "Event b")

    def test_registration_can_not_be_moved_to_an_event_of_another_site(self):
        registration = self.objects["a"][EventRegistration]
        response = self.client.get(self.url(EventRegistration, "edit", registration.pk))
        self.assertNotContains(response, "Event b")

    def test_site_filter_offers_only_own_sites(self):
        response = self.client.get(self.url(People, "list"))
        self.assertContains(response, "Site a")
        self.assertNotContains(response, "Site b")

    def people_form(self, site, first_name):
        return {"site": site.pk, "first_name": first_name, "last_name": "Muster", "slug": first_name.lower()}

    def test_new_object_can_only_be_put_on_an_own_site(self):
        own_site, other_site = self.objects["a"][People].site, self.objects["b"][People].site
        # the same form with the own site works, so the refusal below comes from the site and nothing else
        response = self.client.post(self.url(People, "add"), self.people_form(own_site, "Eva"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(People.objects.filter(first_name="Eva", site=own_site).exists())
        response = self.client.post(self.url(People, "add"), self.people_form(other_site, "Fritz"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(People.objects.filter(first_name="Fritz").exists())

    def test_own_object_can_not_be_moved_to_another_site(self):
        person = self.objects["a"][People]
        own_site, other_site = person.site, self.objects["b"][People].site
        form = self.people_form(own_site, "Anna") | {"slug": person.slug}
        self.assertEqual(self.client.post(self.url(People, "edit", person.pk), form).status_code, 302)
        response = self.client.post(self.url(People, "edit", person.pk), form | {"site": other_site.pk})
        self.assertEqual(response.status_code, 200)
        person.refresh_from_db()
        self.assertEqual(person.site, own_site)

    def registration_form(self, event):
        return {"event": event.pk, "subject": "registration", "name": "Carla a", "email": "carla-a@example.com",
                "telephone": "0123", "message": "hello", "is_member": "on"}

    def test_registration_can_only_be_moved_to_an_own_event(self):
        registration = self.objects["a"][EventRegistration]
        url = self.url(EventRegistration, "edit", registration.pk)
        self.assertEqual(self.client.post(url, self.registration_form(self.events["a"])).status_code, 302)
        self.assertEqual(self.client.post(url, self.registration_form(self.events["b"])).status_code, 200)
        registration.refresh_from_db()
        self.assertEqual(registration.event.pk, self.events["a"].pk)

    def test_new_registration_only_for_an_own_event(self):
        url = self.url(EventRegistration, "add")
        self.assertEqual(self.client.post(url, self.registration_form(self.events["b"])).status_code, 200)
        self.assertFalse(EventRegistration.objects.filter(event=self.events["b"], name="Carla a").exists())
        self.assertEqual(self.client.post(url, self.registration_form(self.events["a"])).status_code, 302)
        self.assertTrue(EventRegistration.objects.filter(event=self.events["a"], name="Carla a").exists())


class ChooserSeparationTest(TwoSitesMixin, TestCase):
    def setUp(self):
        self.client.force_login(self.editors["a"])

    def chooser_url_names(self, model):
        # the chooser of the snippet and the chooser with the site filter used in the pages (base/views.py)
        names = [model.snippet_viewset.chooser_viewset.get_url_name("choose"),
                 model.snippet_viewset.chooser_viewset.get_url_name("choose_results")]
        names += {People: ["people_chooser:choose", "people_chooser:choose_results"],
                  Speaker: ["speaker_chooser:choose", "speaker_chooser:choose_results"]}.get(model, [])
        return names

    def test_chooser_lists_only_own_objects(self):
        for model in (People, Speaker):
            for url_name in self.chooser_url_names(model):
                with self.subTest(model=model._meta.label, url=url_name):
                    response = self.client.get(reverse(url_name))
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, self.objects["a"][model].last_name)
                    self.assertNotContains(response, f"{self.objects['b'][model].first_name} b")

    def test_object_of_another_site_can_not_be_chosen(self):
        for model in (People, Speaker):
            chooser = model.snippet_viewset.chooser_viewset
            for url_name in (chooser.get_url_name("chosen"),
                             {People: "people_chooser:chosen", Speaker: "speaker_chooser:chosen"}[model]):
                with self.subTest(model=model._meta.label, url=url_name):
                    other = self.objects["b"][model]
                    self.assertEqual(self.client.get(reverse(url_name, args=(other.pk,))).status_code, 404)
                    own = self.objects["a"][model]
                    self.assertEqual(self.client.get(reverse(url_name, args=(own.pk,))).status_code, 200)


class SuperuserTest(TwoSitesMixin, TestCase):
    def test_superuser_sees_everything(self):
        self.client.force_login(self.superuser)
        for model in SITE_SCOPED:
            with self.subTest(model=model._meta.label):
                response = self.client.get(self.url(model, "list"))
                for name in ("a", "b"):
                    self.assertContains(response, self.url(model, "edit", self.objects[name][model].pk))
        response = self.client.get(self.url(EventRegistration, "list"))
        self.assertContains(response, self.url(EventRegistration, "edit", self.orphan.pk))

    def test_registration_without_event_is_only_for_superusers(self):
        self.client.force_login(self.editors["a"])
        self.assertEqual(self.client.get(self.url(EventRegistration, "edit", self.orphan.pk)).status_code, 404)


class GetSitesTest(TwoSitesMixin, TestCase):
    """Which sites are a user's own: only those where he may add, change or publish pages."""

    def user_with_page_permission(self, page, codename):
        group = Group.objects.create(name=f"{codename} on {page.title}")
        GroupPagePermission.objects.create(group=group, page=page, permission=Permission.objects.get(
            content_type__app_label="wagtailcore", codename=codename))
        user = User.objects.create_user(f"user-{group.pk}", password="x")
        user.groups.add(group)
        return User.objects.get(pk=user.pk)  # without cached permissions

    def site(self, name):
        return self.objects[name][People].site

    def test_editor_has_his_site(self):
        self.assertEqual(get_sites(User.objects.get(pk=self.editors["a"].pk)), {self.site("a")})

    def test_change_on_a_page_inside_the_site(self):
        user = self.user_with_page_permission(self.events["b"], "change_page")
        self.assertEqual(get_sites(user), {self.site("b")})

    def test_lock_alone_gives_no_site(self):
        user = self.user_with_page_permission(self.site("a").root_page, "lock_page")
        self.assertEqual(get_sites(user), frozenset())

    def test_permission_on_the_root_of_the_tree_gives_all_sites(self):
        user = self.user_with_page_permission(Page.get_first_root_node(), "add_page")
        self.assertEqual(get_sites(user), set(Site.objects.all()))

    def test_inactive_user_has_no_site(self):
        user = User.objects.get(pk=self.editors["a"].pk)
        user.is_active = False
        self.assertEqual(get_sites(user), frozenset())

    def test_inactive_superuser_has_no_site(self):
        user = User.objects.get(pk=self.superuser.pk)
        user.is_active = False
        self.assertEqual(get_sites(user), frozenset())

    def test_superuser_has_all_sites(self):
        self.assertEqual(get_sites(User.objects.get(pk=self.superuser.pk)), set(Site.objects.all()))
