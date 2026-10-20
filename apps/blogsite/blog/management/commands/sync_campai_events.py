import logging
from datetime import timedelta
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from blogsite.blog.models import EventPage, update_or_create_event_from_campai

logger = logging.getLogger(__name__)

# campai returns at most 500 events per request (50 without a limit)
PAGE_SIZE = 500
# events which are over for longer than this are not synced anymore
SYNC_PAST_DAYS = 31


class Command(BaseCommand):
    help = 'Sync'  # @ReservedAssignment

    def handle(self, *args, **options):
        if not settings.CAMPAI_API_URL:
            logger.error("No API_URL set in settings.py.py::settings.CAMPAI_API_URL")
            return
        if not settings.CAMPAI_API_KEY:
            logger.error("No API_KEY set in settings.py.py::settings.CAMPAI_API_KEY")
            return

        events = self.get_events()
        if events is None:
            return

        event_ids = []
        for event in events:
            event_ids.append(event["_id"])
            try:
                # the list contains the full event data, so the event doesn't need to be fetched again
                update_or_create_event_from_campai(event)
            except Exception as e:
                # a single broken event doesn't stop the sync of the others
                logger.exception(e)

        # Unpublish all future events which have been deleted in campai. They are not deleted, so that editors can
        # still see them (and their registrations) in the admin.
        deleted_events = EventPage.objects.live().filter(campai_event_id__isnull=False, start_date__gt=now()).exclude(
            campai_event_id__in=event_ids)
        for event_page in deleted_events:
            logger.info(f'unpublish {event_page}, the event has been deleted in campai')
            event_page.unpublish()

    def get_events(self):
        # Returns the events of the last SYNC_PAST_DAYS and in the future, or None if the list is not complete.
        # Future events missing in the list are deleted, so an error response or an incomplete list must not be
        # returned.
        url = urljoin(settings.CAMPAI_API_URL, 'booking/events/list')
        headers = {"X-API-Key": settings.CAMPAI_API_KEY}
        data = {
            "sort": {},
            "returnCount": True,
            # no passedAvailability filter: it drops cancelled events and events after the end of the booking
            # period, and future ones of them would be deleted below instead of being shown as cancelled/closed
            "fromDate": (now() - timedelta(days=SYNC_PAST_DAYS)).isoformat(),
            "limit": PAGE_SIZE,
            #"hasWaitlist": True,
        }
        events = []
        while True:
            try:
                response = requests.post(url, json=data | {"offset": len(events)}, headers=headers, timeout=10)
                response.raise_for_status()
                page = response.json()
            except Exception as e:
                logger.exception(e)
                return None

            if "events" not in page or "count" not in page:
                logger.error(f"The campai event list has no events or count: {page}")
                return None
            events += page["events"]
            if len(events) >= page["count"]:
                break
            if not page["events"]:
                # campai returns fewer events than it counts, don't ask forever
                break

        if len(events) != page["count"]:
            logger.error(f"The campai event list is incomplete: {len(events)} of {page['count']} events")
            return None
        return events
