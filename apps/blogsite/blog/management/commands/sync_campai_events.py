import json
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import localtime, now

from blogsite.blog.models import EventPage, update_or_create_event_from_campai

logger = logging.getLogger(__name__)

# campai returns at most 500 events per request (50 without a limit)
PAGE_SIZE = 500
# events which are over for longer than this are not synced anymore
SYNC_PAST_DAYS = 31
# Campai is unreachable for a few minutes now and then. Such an outage is only logged as a warning; it is logged as an
# error (which mails the admins) when it lasts longer than OUTAGE_ERROR_AFTER, and then at most every
# OUTAGE_ERROR_INTERVAL.
OUTAGE_ERROR_AFTER = timedelta(minutes=10)
OUTAGE_ERROR_INTERVAL = timedelta(hours=1)
# The start of the current outage is kept in a file, because every cron run is a new process. The file is in the
# container, so a new container starts without an outage.
OUTAGE_FILE = Path(tempfile.gettempdir()) / 'sync_campai_events.outage'


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
            except (requests.ConnectionError, requests.Timeout) as e:
                self.campai_unreachable(e)
                return None
            if response.status_code >= 500:
                self.campai_unreachable(f"Campai answered {url} with HTTP {response.status_code}.")
                return None

            try:
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

        self.campai_reachable()
        if len(events) != page["count"]:
            logger.error(f"The campai event list is incomplete: {len(events)} of {page['count']} events")
            return None
        return events

    def campai_unreachable(self, error):
        # Logs a warning for a short outage and an error for a long one, see OUTAGE_ERROR_AFTER.
        current_time = now()
        outage = read_outage()
        if outage is None:
            outage = {"since": current_time, "last_error": None}

        duration = current_time - outage["since"]
        since = f"{localtime(outage['since']):%Y-%m-%d %H:%M}"
        if duration < OUTAGE_ERROR_AFTER:
            logger.warning(f"Campai is unreachable since {since}: {error}")
        elif outage["last_error"] is None or current_time - outage["last_error"] >= OUTAGE_ERROR_INTERVAL:
            minutes = int(duration.total_seconds() // 60)
            logger.error(f"Campai is unreachable for {minutes} minutes (since {since}): {error}")
            outage["last_error"] = current_time
        else:
            # the admins already got a mail for this outage less than OUTAGE_ERROR_INTERVAL ago
            logger.warning(f"Campai is still unreachable since {since}: {error}")
        write_outage(outage)

    def campai_reachable(self):
        outage = read_outage()
        if outage is None:
            return
        logger.info(f"Campai is reachable again after an outage since {localtime(outage['since']):%Y-%m-%d %H:%M}.")
        OUTAGE_FILE.unlink(missing_ok=True)


def read_outage():
    # Returns the current outage as {"since": datetime, "last_error": datetime or None}, or None without an outage.
    try:
        data = json.loads(OUTAGE_FILE.read_text())
        last_error = data["last_error"]
        return {
            "since": datetime.fromisoformat(data["since"]),
            "last_error": datetime.fromisoformat(last_error) if last_error else None,
        }
    except FileNotFoundError:
        return None
    except (ValueError, KeyError, TypeError) as e:
        # a broken file must not stop the sync, the outage then starts again with this run
        logger.warning(f"Could not read {OUTAGE_FILE}, ignoring it: {e}")
        return None


def write_outage(outage):
    last_error = outage["last_error"]
    data = {
        "since": outage["since"].isoformat(),
        "last_error": last_error.isoformat() if last_error else None,
    }
    OUTAGE_FILE.write_text(json.dumps(data))
