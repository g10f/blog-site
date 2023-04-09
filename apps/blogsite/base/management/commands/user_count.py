import logging

from django.core.management.base import BaseCommand

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Countusers'  # @ReservedAssignment

    def handle(self, *args, **options):
        print(get_user_model().objects.count())
