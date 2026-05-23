import logging
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from blogsite.blog.models import EventPage, update_or_create_event_from_campai

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync'  # @ReservedAssignment

    def handle(self, *args, **options):
        data = {
              "sort": {},
              "returnCount": True,
              "passedAvailability": False,
              "hasWaitlist": True,
            }
        if not settings.CAMPAI_API_URL:
            logger.error("No API_URL set in settings.py.py::settings.CAMPAI_API_URL")
            return
        if not settings.CAMPAI_API_KEY:
            logger.error("No API_KEY set in settings.py.py::settings.CAMPAI_API_KEY")
            return

        url = urljoin(settings.CAMPAI_API_URL, f'booking/events/list')
        headers = {"X-API-Key": settings.CAMPAI_API_KEY}
        try:
            event_ids = []
            events = requests.post(url, json=data, headers=headers, timeout=10).json()
            if "events" in events:
                for event in events["events"]:
                    event_ids.append(event["_id"])
                    update_or_create_event_from_campai(event["_id"])

            # delete all future events with campai_event_id not in the list event["_id"]
            EventPage.objects.filter(campai_event_id__isnull=False, start_date__gt=now()).exclude(campai_event_id__in=event_ids).delete()
        except Exception as e:
            logger.exception(e)
