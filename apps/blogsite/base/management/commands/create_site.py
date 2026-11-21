from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.template import Context, Template
from django.utils.text import slugify
from wagtail.images.models import Image
from wagtail.models import Collection, Page, Site
from wagtail.rich_text import RichText

from blogsite.base.editors import check_editor_groups, editor_groups, get_or_create_collection, set_editor_groups
from blogsite.base.models import FooterText, HomePage, PersonsPage, SiteLogo, StandardPage
from blogsite.blog.models import BlogIndexPage, BlogPage

# The files of a site template (like the template of "django-admin startproject"). The theme brings its own in
# <theme package>/site_template/, e.g. afd_theme/site_template/ in the repo afd-blog.
TEMPLATE_FILES = ["logo-header.png", "logo-footer.png", "footer.html", "impressum.html", "datenschutzerklaerung.html"]

# The footer of the template links to these addresses, so the slugs are fixed.
IMPRINT_SLUG = "impressum"
PRIVACY_SLUG = "datenschutzerklaerung"

EXAMPLE_POST_INTRODUCTION = ("Dies ist ein Beispiel. Ändern Sie diesen Beitrag oder legen Sie unter "
                             "„Artikel“ mit „Seite hinzufügen“ einen neuen an.")


class Command(BaseCommand):
    help = ("Creates a new site with a fixed structure: home page, 'Artikel' (blog index) with an example post, "
            "a page for the people, imprint and privacy policy, all as drafts; and its own logo, footer, "
            "collection and editor group (blogsite/base/editors.py). Texts and pictures come from the site "
            "template of the theme (<theme>/site_template/) or --template. Nothing is taken from other sites.")

    def add_arguments(self, parser):
        parser.add_argument("--hostname", required=True, help="domain of the new site, e.g. afd-wolfsburg.de")
        parser.add_argument("--site-name", required=True, help="official name, e.g. 'AfD-Kreisverband Wolfsburg'")
        parser.add_argument("--people-title", required=True, help="title of the page with the people, e.g. Vorstand")
        parser.add_argument("--group", required=True, help="editor group, e.g. 'Kreisverband Wolfsburg Redaktion'")
        parser.add_argument("--role", required=True, help="role in Keycloak, e.g. kreisverband-wolfsburg-redaktion")
        parser.add_argument("--collection", required=True, help="collection for images and documents, e.g. 'KV Wolfsburg'")
        parser.add_argument("--shared-collection", action="append", default=[],
                            help="an existing collection the editors may choose images and documents from")
        parser.add_argument("--template", help="directory of the site template (default: site_template of the theme)")

    @transaction.atomic
    def handle(self, *args, **options):
        hostname, site_name = options["hostname"], options["site_name"]
        template_dir = self.get_template_dir(options["template"])
        if Site.objects.filter(hostname=hostname).exists():
            raise CommandError(f"There is already a site {hostname}.")
        root = Page.get_first_root_node()
        home_slug = slugify(hostname.replace(".", "-"))
        if root.get_children().filter(slug=home_slug).exists():
            raise CommandError(f"There is already a page with the slug {home_slug} at the top of the page tree.")
        shared = []
        for name in options["shared_collection"]:
            collection = Collection.objects.filter(name=name).first()
            if collection is None:
                raise CommandError(f"There is no collection '{name}'.")
            shared.append(collection)
        people_slug = slugify(options["people_title"])
        if not people_slug or people_slug in ("artikel", IMPRINT_SLUG, PRIVACY_SLUG):
            raise CommandError(f"The people page can't be called '{options['people_title']}': its address would be "
                               f"'/{people_slug}/', which is empty or taken by another page of the site.")
        # checked before anything is written: the logo pictures go to the media storage, which a rollback of the
        # database doesn't clean up
        try:
            check_editor_groups(options["group"], options["role"])
        except ValueError as error:
            raise CommandError(str(error))

        def render(file_name):
            text = (template_dir / file_name).read_text(encoding="utf-8")
            return Template(text).render(Context({"site_name": site_name}))

        def add_draft(parent, page):
            page.live = False
            parent.add_child(instance=page)
            page.save_revision()
            return page

        home = add_draft(root, HomePage(title=site_name, slug=home_slug, show_in_menus=True))
        blog_index = add_draft(home, BlogIndexPage(title="Artikel", slug="artikel", show_in_menus=True))
        add_draft(blog_index, BlogPage(title="Beispiel-Beitrag", slug="beispiel-beitrag",
                                       introduction=EXAMPLE_POST_INTRODUCTION))
        add_draft(home, PersonsPage(title=options["people_title"], slug=people_slug,
                                    show_in_menus=True))
        add_draft(home, StandardPage(title="Impressum", slug=IMPRINT_SLUG,
                                     body=[("paragraph_block", RichText(render("impressum.html")))]))
        add_draft(home, StandardPage(title="Datenschutzerklärung", slug=PRIVACY_SLUG,
                                     body=[("paragraph_block", RichText(render("datenschutzerklaerung.html")))]))

        site = Site.objects.create(hostname=hostname, site_name=site_name, root_page=home)
        try:
            collection = get_or_create_collection(options["collection"])
            done = set_editor_groups(site, options["group"], options["role"], collection, shared)
        except ValueError as error:
            raise CommandError(str(error))

        images = []
        try:
            def add_image(file_name, title):
                with open(template_dir / file_name, "rb") as file:
                    image = Image.objects.create(title=title, collection=collection,
                                                 file=ImageFile(file, name=f"{home_slug}-{file_name}"))
                images.append(image)
                return image

            header = add_image("logo-header.png", f"{site_name} Logo")
            footer_image = add_image("logo-footer.png", f"{site_name} Logo klein")
            logo = SiteLogo.objects.create(site=site, image_header=header, image_footer=footer_image,
                                           image_ico=footer_image, live=True)
            logo.save_revision().publish()
            footer = FooterText.objects.create(site=site, body=render("footer.html"), live=True)
            footer.save_revision().publish()
        except Exception:
            # the database is rolled back, the files in the media storage are not
            for image in images:
                image.file.delete(save=False)
            raise

        self.stdout.write(f"site {site.pk} {hostname} with the template {template_dir}; pages (all drafts):")
        for page in Page.objects.descendant_of(home, inclusive=True).order_by("path"):
            self.stdout.write(f"  {page.pk} {page.specific_class.__name__} '{page.title}' {page.url_path}")
        self.stdout.write("logo, footer text")
        for line in done:
            self.stdout.write(line)
        self.stdout.write(
            "Next: fill in the [placeholders] of the imprint and the privacy policy and publish the pages; the "
            "domain in the inventory and in the Keycloak client, the roles "
            f"{' and '.join(role for _, role in editor_groups(options['group'], options['role']))} in Keycloak; "
            "the domain as a site in Plausible (statistics, named in the privacy policy). In a new instance turn "
            "off the workflow 'Moderators approval' (Settings > Workflows), the editors publish themselves.")

    def get_template_dir(self, path):
        if path:
            template_dir = Path(path)
        else:
            theme = getattr(settings, "THEME", None)
            if not theme:
                raise CommandError("No theme is installed (setting THEME); name a site template with --template.")
            template_dir = Path(apps.get_app_config(theme.rsplit(".", 1)[-1]).path) / "site_template"
        missing = [name for name in TEMPLATE_FILES if not (template_dir / name).is_file()]
        if missing:
            raise CommandError(f"The site template {template_dir} lacks {', '.join(missing)}.")
        return template_dir
