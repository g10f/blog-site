"""The editor group of a site (editors.py), the protection of the structure pages and the command create_site."""
import re
import shutil
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.auth.models import Group, Permission
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.images.permissions import permission_policy as image_policy
from wagtail.documents.permissions import permission_policy as document_policy
from wagtail.images.tests.utils import get_test_image_file, get_test_image_file_jpeg
from wagtail.models import Collection, GroupPagePermission, Page, Site

from blogsite.base.editors import get_or_create_collection, set_editor_groups
from blogsite.base.models import FooterText, HomePage, SiteLogo, StandardPage
from blogsite.base.site import get_sites
from blogsite.base.wagtail_hooks import STRUCTURE_PAGE_MESSAGE
from blogsite.blog.models import BlogIndexPage, BlogPage
from oidc.models import RoleGroup

User = get_user_model()

IMPRINT = "<p>{{ site_name }}<br/>p. Adr. [Name des Verantwortlichen]</p>"
PRIVACY = "<h2>Geltungsbereich</h2><p>{{ site_name }}, [E-Mail-Adresse]</p>"
FOOTER = '<a href="/impressum/">Impressum</a> <a href="/datenschutzerklaerung/">Datenschutzerklärung</a>'
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">' \
      '<rect width="{width}" height="{height}" fill="{fill}"/></svg>'


class SiteTemplateMixin:
    """A site template in a temporary directory, and a temporary MEDIA_ROOT for the logo pictures."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.template_dir = cls.temp_dir / "site_template"
        cls.template_dir.mkdir()
        for name, width, height in (("logo-header.svg", 2000, 660), ("logo-header-dark.svg", 2000, 660),
                                    ("logo-footer.svg", 800, 800), ("logo-footer-dark.svg", 800, 800)):
            fill = "#fff" if "dark" in name else "#000"
            (cls.template_dir / name).write_text(SVG.format(width=width, height=height, fill=fill), encoding="utf-8")
        (cls.template_dir / "logo-ico.png").write_bytes(get_test_image_file().file.getvalue())
        for name in ("image-home.jpg", "image-articles.jpg"):
            (cls.template_dir / name).write_bytes(get_test_image_file_jpeg().file.getvalue())
        (cls.template_dir / "impressum.html").write_text(IMPRINT, encoding="utf-8")
        (cls.template_dir / "datenschutzerklaerung.html").write_text(PRIVACY, encoding="utf-8")
        (cls.template_dir / "footer.html").write_text(FOOTER, encoding="utf-8")
        cls.media_settings = override_settings(MEDIA_ROOT=str(cls.temp_dir / "media"))
        cls.media_settings.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_settings.disable()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    @classmethod
    def create_site(cls, **options):
        arguments = {"hostname": "new.example.com", "site_name": "AfD-Fraktion Neustadt", "people_title": "Fraktion",
                     "group": "Fraktion Neustadt Redaktion", "role": "fraktion-neustadt-redaktion",
                     "collection": "Fraktion Neustadt", "template": str(cls.template_dir)}
        arguments.update(options)
        call_command("create_site", *[f"--{name.replace('_', '-')}={value}" for name, value in arguments.items()],
                     stdout=StringIO())
        return Site.objects.get(hostname=arguments["hostname"])

    @classmethod
    def create_other_site(cls):
        """Another organisation in the same instance, with its own imprint."""
        home = Page.get_first_root_node().add_child(instance=HomePage(title="Other", slug="other"))
        home.add_child(instance=StandardPage(title="Impressum", slug="impressum", body=[
            ("paragraph_block", "<p>Imprint of the other organisation</p>")]))
        return Site.objects.create(hostname="other.example.com", root_page=home, site_name="Other")


class CreateSiteTest(SiteTemplateMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.other = cls.create_other_site()
        cls.site = cls.create_site()
        cls.home = cls.site.root_page

    def page(self, title):
        return Page.objects.descendant_of(self.home, inclusive=True).get(title=title).specific

    def test_fixed_structure(self):
        pages = Page.objects.descendant_of(self.home, inclusive=True).specific().order_by("path")
        self.assertEqual([(type(page).__name__, page.title, page.url_path) for page in pages], [
            ("HomePage", "AfD-Fraktion Neustadt", "/new-example-com/"),
            ("BlogIndexPage", "Artikel", "/new-example-com/artikel/"),
            ("BlogPage", "Beispiel-Beitrag", "/new-example-com/artikel/beispiel-beitrag/"),
            ("PersonsPage", "Fraktion", "/new-example-com/fraktion/"),
            ("StandardPage", "Impressum", "/new-example-com/impressum/"),
            ("StandardPage", "Datenschutzerklärung", "/new-example-com/datenschutzerklaerung/"),
        ])

    def test_all_pages_are_drafts(self):
        self.assertFalse(Page.objects.descendant_of(self.home, inclusive=True).filter(live=True).exists())

    def test_texts_come_from_the_template_with_the_name_of_the_site(self):
        imprint = str(self.page("Impressum").body)
        self.assertIn("AfD-Fraktion Neustadt", imprint)
        self.assertIn("[Name des Verantwortlichen]", imprint)
        self.assertNotIn("{{", imprint)
        self.assertNotIn("other organisation", imprint)
        self.assertIn("[E-Mail-Adresse]", str(self.page("Datenschutzerklärung").body))

    def test_own_logo_and_footer(self):
        logo = SiteLogo.objects.get(site=self.site)
        collection = Collection.objects.get(name="Fraktion Neustadt")
        self.assertEqual(logo.image_header.collection, collection)
        # the logos stay SVGs; the favicon is a PNG of its own, as base.html converts it to PNG
        self.assertTrue(logo.image_header.is_svg())
        self.assertTrue(logo.image_footer.is_svg())
        self.assertFalse(logo.image_ico.is_svg())
        self.assertTrue(logo.live)
        footer = FooterText.objects.get(site=self.site)
        self.assertIn('href="/datenschutzerklaerung/"', footer.body)
        self.assertTrue(footer.live)

    def test_logo_for_the_dark_color_mode(self):
        logo = SiteLogo.objects.get(site=self.site)
        self.assertNotEqual(logo.image_header_dark, logo.image_header)
        self.assertNotEqual(logo.image_footer_dark, logo.image_footer)
        # both variants are on the page, the CSS in base.html shows the one of the color mode
        self.home.specific.save_revision().publish()
        response = self.client.get("/", headers={"host": "new.example.com"})
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # header, header on small screens, footer
        self.assertEqual(len(re.findall(r'<img [^>]*class="[^"]*\blogo-light\b', html)), 3)
        self.assertEqual(len(re.findall(r'<img [^>]*class="[^"]*\blogo-dark\b', html)), 3)
        self.assertIn("[data-bs-theme=dark] .logo-dark", html)
        # the footer logo is shown with 64 pixels, the SVG is delivered as it is
        footer = html[html.index("<footer"):]
        self.assertRegex(footer, r'<img src="[^"]+\.svg" width="64" height="64" class="me-3 logo-light"')

    def test_site_without_dark_logo_shows_its_logo_in_both_modes(self):
        # sites created before the dark variant existed have none: only the normal logo, without logo-light/-dark
        SiteLogo.objects.filter(site=self.site).update(image_header_dark=None, image_footer_dark=None)
        self.home.specific.save_revision().publish()
        response = self.client.get("/", headers={"host": "new.example.com"})
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotRegex(html, r'<img [^>]*class="[^"]*\blogo-(light|dark)\b')
        footer = html[html.index("<footer"):]
        self.assertRegex(footer, r'<img src="[^"]+\.svg" width="64" height="64" class="me-3"')

    def test_failure_after_the_pictures_leaves_no_files(self):
        # the database is rolled back by the transaction, the media files are removed by create_site itself
        files_before = sorted((self.temp_dir / "media").rglob("*.*"))
        with mock.patch.object(FooterText.objects, "create", side_effect=RuntimeError("failure for the test")):
            with self.assertRaisesMessage(RuntimeError, "failure for the test"):
                self.create_site(hostname="f.example.com")
        self.assertEqual(sorted((self.temp_dir / "media").rglob("*.*")), files_before)
        self.assertFalse(Site.objects.filter(hostname="f.example.com").exists())

    def test_pictures_of_the_home_page_and_the_articles(self):
        # the editor works on the latest revision, so the picture has to be in there, not only in the page
        collection = Collection.objects.get(name="Fraktion Neustadt")
        for title in ("AfD-Fraktion Neustadt", "Artikel"):
            page = self.page(title)
            self.assertEqual(page.image.collection, collection)
            self.assertEqual(page.revisions.count(), 1)
            self.assertEqual(page.get_latest_revision_as_object().image, page.image)

    def test_editor_groups_with_roles(self):
        for name, role in (("Fraktion Neustadt Redaktion", "fraktion-neustadt-redaktion"),
                           ("Fraktion Neustadt Redaktion erweitert", "fraktion-neustadt-redaktion-erweitert")):
            self.assertEqual(RoleGroup.objects.get(group__name=name).role, role)

    def test_logo_and_footer_are_published_without_pending_changes(self):
        for snippet in (SiteLogo.objects.get(site=self.site), FooterText.objects.get(site=self.site)):
            self.assertTrue(snippet.live)
            self.assertFalse(snippet.has_unpublished_changes)
            self.assertIsNotNone(snippet.live_revision)

    def test_people_page_title_that_takes_another_address_is_refused(self):
        with self.assertRaisesMessage(CommandError, "The people page can't be called 'Impressum'"):
            self.create_site(hostname="y.example.com", people_title="Impressum")

    def test_role_conflict_is_refused_before_any_file_is_written(self):
        RoleGroup.objects.create(group=Group.objects.create(name="Other"), role="taken-erweitert")
        files_before = sorted((self.temp_dir / "media").rglob("*"))
        with self.assertRaisesMessage(CommandError, "already belongs to the group 'Other'"):
            self.create_site(hostname="z.example.com", role="taken")
        self.assertEqual(sorted((self.temp_dir / "media").rglob("*")), files_before)
        self.assertFalse(Site.objects.filter(hostname="z.example.com").exists())

    def test_the_other_site_is_unchanged(self):
        self.assertEqual(Page.objects.descendant_of(self.other.root_page, inclusive=True).count(), 2)
        self.assertFalse(SiteLogo.objects.filter(site=self.other).exists())

    def test_existing_hostname_is_refused(self):
        with self.assertRaisesMessage(CommandError, "There is already a site new.example.com."):
            self.create_site()

    def test_incomplete_template_is_refused(self):
        empty = self.temp_dir / "empty"
        empty.mkdir(exist_ok=True)
        with self.assertRaisesMessage(CommandError, "lacks logo-header.svg"):
            self.create_site(hostname="x.example.com", template=str(empty))
        self.assertFalse(Site.objects.filter(hostname="x.example.com").exists())


class EditorRightsTest(SiteTemplateMixin, TestCase):
    """What a member of the editor group may do: change everything of his site, add and remove blog posts only."""

    @classmethod
    def setUpTestData(cls):
        cls.other = cls.create_other_site()
        cls.shared = get_or_create_collection("AfD")
        cls.site = cls.create_site(shared_collection="AfD")
        cls.editor = User.objects.create_user("editor", password="x")
        cls.editor.groups.add(Group.objects.get(name="Fraktion Neustadt Redaktion"))
        for page in Page.objects.descendant_of(cls.site.root_page, inclusive=True).order_by("path"):
            page.specific.save_revision().publish()

    def setUp(self):
        self.client.force_login(self.editor)

    def page(self, title):
        return Page.objects.descendant_of(self.site.root_page, inclusive=True).get(title=title)

    def test_may_change_and_publish_every_page_of_his_site(self):
        for page in Page.objects.descendant_of(self.site.root_page, inclusive=True):
            permissions = page.permissions_for_user(self.editor)
            self.assertTrue(permissions.can_edit(), page.title)
            self.assertTrue(permissions.can_publish(), page.title)
            response = self.client.get(reverse("wagtailadmin_pages:edit", args=[page.pk]))
            self.assertEqual(response.status_code, 200, page.title)

    def test_may_add_only_below_the_blog_index(self):
        for title in ("AfD-Fraktion Neustadt", "Fraktion", "Impressum"):
            self.assertFalse(self.page(title).permissions_for_user(self.editor).can_add_subpage(), title)
        self.assertTrue(self.page("Artikel").permissions_for_user(self.editor).can_add_subpage())

    def test_add_page_opens_the_blog_post_form_directly(self):
        blog_index = self.page("Artikel")
        response = self.client.get(reverse("wagtailadmin_pages:add_subpage", args=[blog_index.pk]))
        self.assertRedirects(response, reverse("wagtailadmin_pages:add", args=["blog", "blogpage", blog_index.pk]))

    def test_no_rights_on_the_other_site(self):
        for page in Page.objects.descendant_of(self.other.root_page, inclusive=True):
            self.assertFalse(page.permissions_for_user(self.editor).can_edit(), page.title)
        self.assertEqual(get_sites(self.editor), frozenset({self.site}))

    def test_may_delete_a_blog_post(self):
        post = self.page("Beispiel-Beitrag")
        self.client.post(reverse("wagtailadmin_pages:delete", args=[post.pk]))
        self.assertFalse(Page.objects.filter(pk=post.pk).exists())

    def test_may_not_delete_a_structure_page(self):
        for title in ("Impressum", "Fraktion"):
            page = self.page(title)
            response = self.client.post(reverse("wagtailadmin_pages:delete", args=[page.pk]))
            self.assertTrue(Page.objects.filter(pk=page.pk).exists(), title)
            self.assertRedirects(response, reverse("wagtailadmin_explore", args=[page.get_parent().pk]),
                                 fetch_redirect_response=False)
            self.assertIn(STRUCTURE_PAGE_MESSAGE % {"title": title},
                          [str(message) for message in get_messages(response.wsgi_request)])

    def test_may_not_unpublish_the_home_page(self):
        home = self.page("AfD-Fraktion Neustadt")
        self.client.post(reverse("wagtailadmin_pages:unpublish", args=[home.pk]), {"include_descendants": "on"})
        self.assertTrue(Page.objects.get(pk=home.pk).live)
        self.assertTrue(Page.objects.get(pk=self.page("Impressum").pk).live)

    def test_may_not_delete_structure_pages_in_bulk(self):
        imprint, post = self.page("Impressum"), self.page("Beispiel-Beitrag")
        url = reverse("wagtail_bulk_action", args=["wagtailcore", "page", "delete"])
        self.client.post(f"{url}?id={imprint.pk}&id={post.pk}")
        self.assertTrue(Page.objects.filter(pk=imprint.pk).exists())
        self.assertTrue(Page.objects.filter(pk=post.pk).exists())

    def test_images_and_documents_of_his_collection(self):
        own = Collection.objects.get(name="Fraktion Neustadt")
        for policy in (image_policy, document_policy):
            self.assertEqual(set(policy.collections_user_has_permission_for(self.editor, "add")), {own})
            self.assertEqual(set(policy.collections_user_has_permission_for(self.editor, "change")), {own})
            self.assertEqual(set(policy.collections_user_has_permission_for(self.editor, "choose")),
                             {own, self.shared})

    def test_people_of_his_site(self):
        response = self.client.get(reverse("wagtailsnippets_base_people:list"))
        self.assertEqual(response.status_code, 200)


class AdvancedEditorRightsTest(SiteTemplateMixin, TestCase):
    """The advanced editors: add every page type in the site and remove what they could add again."""

    @classmethod
    def setUpTestData(cls):
        cls.site = cls.create_site()
        cls.editor = User.objects.create_user("advanced", password="x")
        cls.editor.groups.add(Group.objects.get(name="Fraktion Neustadt Redaktion erweitert"))
        for page in Page.objects.descendant_of(cls.site.root_page, inclusive=True).order_by("path"):
            page.specific.save_revision().publish()

    def setUp(self):
        self.client.force_login(self.editor)

    def page(self, title):
        return Page.objects.descendant_of(self.site.root_page, inclusive=True).get(title=title)

    def test_may_add_below_the_home_page(self):
        self.assertTrue(self.page("AfD-Fraktion Neustadt").permissions_for_user(self.editor).can_add_subpage())

    def test_may_delete_a_structure_page(self):
        imprint = self.page("Impressum")
        self.client.post(reverse("wagtailadmin_pages:delete", args=[imprint.pk]))
        self.assertFalse(Page.objects.filter(pk=imprint.pk).exists())

    def test_may_not_unpublish_the_home_page(self):
        home = self.page("AfD-Fraktion Neustadt")
        self.client.post(reverse("wagtailadmin_pages:unpublish", args=[home.pk]), {"include_descendants": "on"})
        self.assertTrue(Page.objects.get(pk=home.pk).live)


class GroupsOfOtherInstancesTest(TestCase):
    """A group that may add pages everywhere, as the editors of the other blog instances, keeps its rights."""

    def test_may_delete_a_standard_page(self):
        home = Page.get_first_root_node().add_child(instance=HomePage(title="Home", slug="home-vfk"))
        page = home.add_child(instance=StandardPage(title="Über uns", slug="ueber-uns"))
        group = Group.objects.create(name="Moderators of another instance")
        group.permissions.add(Permission.objects.get(codename="access_admin"))
        for codename in ("add_page", "change_page", "publish_page"):
            GroupPagePermission.objects.create(group=group, page=Page.get_first_root_node(),
                                               permission=Permission.objects.get(
                                                   content_type__app_label="wagtailcore", codename=codename))
        moderator = User.objects.create_user("moderator", password="x")
        moderator.groups.add(group)
        self.client.force_login(moderator)
        self.client.post(reverse("wagtailadmin_pages:delete", args=[page.pk]))
        self.assertFalse(Page.objects.filter(pk=page.pk).exists())


class SetEditorGroupTest(SiteTemplateMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.site = cls.create_site()
        cls.collection = Collection.objects.get(name="Fraktion Neustadt")
        cls.group = Group.objects.get(name="Fraktion Neustadt Redaktion")

    def test_rights_given_by_hand_are_removed_and_reported(self):
        self.group.permissions.add(*Group.permissions.field.related_model.objects.filter(codename="add_speaker"))
        done = set_editor_groups(self.site, self.group.name, "fraktion-neustadt-redaktion", self.collection)
        self.assertNotIn("add_speaker", set(self.group.permissions.values_list("codename", flat=True)))
        self.assertIn("  REMOVED: base.add_speaker", done)

    def test_running_it_twice_changes_nothing(self):
        before = set(self.group.page_permissions.values_list("page_id", "permission_id"))
        done = set_editor_groups(self.site, self.group.name, "fraktion-neustadt-redaktion", self.collection)
        self.assertEqual(set(self.group.page_permissions.values_list("page_id", "permission_id")), before)
        self.assertFalse([line for line in done if "REMOVED" in line])
        self.assertEqual(RoleGroup.objects.filter(role="fraktion-neustadt-redaktion").count(), 1)

    def test_a_new_blog_index_gets_the_add_right_after_running_it_again(self):
        new_index = self.site.root_page.add_child(instance=BlogIndexPage(title="Presse", slug="presse"))
        set_editor_groups(self.site, self.group.name, "fraktion-neustadt-redaktion", self.collection)
        self.assertTrue(self.group.page_permissions.filter(page=new_index, permission__codename="add_page").exists())

    def test_a_role_of_another_group_is_refused(self):
        RoleGroup.objects.create(group=Group.objects.create(name="Other"), role="taken")
        with self.assertRaisesMessage(ValueError, "already belongs to the group 'Other'"):
            set_editor_groups(self.site, self.group.name, "taken", self.collection)

    def test_a_site_without_blog_index_is_refused(self):
        home = Page.get_first_root_node().add_child(instance=HomePage(title="Bare", slug="bare"))
        bare = Site.objects.create(hostname="bare.example.com", root_page=home)
        with self.assertRaisesMessage(ValueError, "has no blog index page"):
            set_editor_groups(bare, "Bare Redaktion", "bare-redaktion", self.collection)
