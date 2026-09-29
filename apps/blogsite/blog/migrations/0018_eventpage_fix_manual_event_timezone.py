# Events entered manually in the Wagtail admin while TIME_ZONE was 'UTC' hold the German wall clock
# time as UTC (e.g. 19:00 meant 19:00 Europe/Berlin, but was stored as 19:00 UTC).
# With TIME_ZONE = 'Europe/Berlin' these values have to be reinterpreted as local time.
# Events imported from Campai (campai_event_id set) already contain real UTC values and are not touched.
from datetime import timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.db import migrations
from django.db.models import Q
from django.utils.dateparse import parse_datetime

BERLIN = ZoneInfo('Europe/Berlin')
DATE_FIELDS = ('start_date', 'end_date', 'registration_end_date')


def utc_wall_clock_to_berlin(value):
    # 19:00 UTC -> 19:00 Europe/Berlin (= 17:00 UTC in summer)
    return value.replace(tzinfo=None).replace(tzinfo=BERLIN).astimezone(dt_timezone.utc)


def berlin_to_utc_wall_clock(value):
    # 19:00 Europe/Berlin -> 19:00 UTC
    return value.astimezone(BERLIN).replace(tzinfo=dt_timezone.utc)


def convert_revision_value(value, convert):
    dt = parse_datetime(value) if value else None
    if dt is None:
        return value
    return convert(dt).isoformat().replace('+00:00', 'Z')


def convert_events(apps, convert):
    EventPage = apps.get_model('blog', 'EventPage')
    Revision = apps.get_model('wagtailcore', 'Revision')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    events = EventPage.objects.filter(Q(campai_event_id__isnull=True) | Q(campai_event_id=''))
    for event in events:
        values = {name: convert(getattr(event, name)) for name in DATE_FIELDS if getattr(event, name) is not None}
        EventPage.objects.filter(pk=event.pk).update(**values)

    try:
        content_type = ContentType.objects.get(app_label='blog', model='eventpage')
    except ContentType.DoesNotExist:
        return
    event_ids = [str(pk) for pk in events.values_list('pk', flat=True)]
    for revision in Revision.objects.filter(content_type=content_type, object_id__in=event_ids):
        for name in DATE_FIELDS:
            if name in revision.content:
                revision.content[name] = convert_revision_value(revision.content[name], convert)
        revision.save(update_fields=['content'])


def forwards(apps, schema_editor):
    convert_events(apps, utc_wall_clock_to_berlin)


def backwards(apps, schema_editor):
    convert_events(apps, berlin_to_utc_wall_clock)


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0017_eventpage_campai_event_id'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('wagtailcore', '0091_remove_revision_submitted_for_moderation'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
