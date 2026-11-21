from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.models import Collection, Site

from blogsite.base.editors import get_or_create_collection, set_editor_groups


class Command(BaseCommand):
    help = ("Creates or updates the two editor groups of a site with the rights of blogsite/base/editors.py: "
            "'<group>' (change and publish all pages of the site, add blog posts only) and '<group> erweitert' "
            "(role '<role>-erweitert', may also add every page type). This is a reset: rights the groups had "
            "before and not in this list are removed and listed as REMOVED. Run it again after adding a blog "
            "index page.")

    def add_arguments(self, parser):
        parser.add_argument("--site", required=True, help="hostname of the site, e.g. afd-braunschweig.de")
        parser.add_argument("--group", required=True, help="name of the group, e.g. 'Kreisverband Braunschweig Redaktion'")
        parser.add_argument("--role", required=True, help="role in Keycloak, e.g. kreisverband-braunschweig-redaktion")
        parser.add_argument("--collection", required=True,
                            help="collection for the images and documents of the site, created if missing; "
                                 "'Root' for an instance with one site")
        parser.add_argument("--shared-collection", action="append", default=[],
                            help="an existing collection the editors may choose images and documents from "
                                 "(may be given several times)")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            site = Site.objects.select_related("root_page").get(hostname=options["site"])
        except Site.DoesNotExist:
            raise CommandError(f"There is no site with the hostname {options['site']}.")
        shared = []
        for name in options["shared_collection"]:
            collection = Collection.objects.filter(name=name).first()
            if collection is None:
                raise CommandError(f"There is no collection '{name}'.")
            shared.append(collection)
        try:
            done = set_editor_groups(site, options["group"], options["role"],
                                     get_or_create_collection(options["collection"]), shared)
        except ValueError as error:
            raise CommandError(str(error))
        for line in done:
            self.stdout.write(line)
