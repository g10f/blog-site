import django_filters
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.panels import ObjectList
from wagtail.snippets.views.snippets import SnippetViewSet

from blogsite.base.site import get_sites, pages_of_sites, sees_all_sites
from blogsite.base.views import SiteScopedViewSetMixin
from .models import EventRegistration, EventPage


def events_of_user(user):
    """The events a user may see registrations of: all for a superuser, otherwise those of his sites."""
    events = EventPage.objects.all()
    if sees_all_sites(user):
        return events
    return events.filter(pages_of_sites(get_sites(user)))


def events_of_request(request):
    if request is None:
        return EventPage.objects.none()
    return events_of_user(request.user).filter(event__isnull=False).distinct().order_by('-start_date')


class EventFilter(WagtailFilterSet):
    # only the events of the user's sites: the titles of the other sites' events are not his business
    event = django_filters.ModelChoiceFilter(queryset=events_of_request)

    # email = django_filters.CharFilter(lookup_expr='icontains', label='Email')
    # year = django_filters.NumberFilter(field_name="event__start_date", lookup_expr='year', min_value=2023, label='Year')

    # def __init__(self, data=None, *args, **kwargs):
    #     # if filterset is bound, use initial values as defaults
    #     if data is not None:
    #         # get a mutable copy of the QueryDict
    #         data = data.copy()
    #
    #         # filter param is either missing or empty, use initial as default
    #         if not data.get('year'):
    #             data['year'] = now().year
    #
    #     super().__init__(data, *args, **kwargs)

    class Meta:
        model = EventRegistration
        fields = ['event', ]


class EventRegistrationAdminForm(WagtailAdminModelForm):
    """The edit form of a registration: it can only be moved to an event of the user's own sites."""

    def __init__(self, *args, for_user=None, **kwargs):
        super().__init__(*args, for_user=for_user, **kwargs)
        if for_user is not None and 'event' in self.fields:
            self.fields['event'].queryset = events_of_user(for_user)


class EventRegistrationAdmin(SiteScopedViewSetMixin, SnippetViewSet):
    """
    Registrations hold name, mail, telephone and membership of the people who registered. An editor only sees
    those of the events on his own sites (EventPageSitePermissionPolicy, registered in wagtail_hooks.py); a
    registration whose event was deleted is only seen by superusers.
    """
    icon = 'mail'
    model = EventRegistration
    add_to_admin_menu = True
    menu_icon = 'mail'
    search_fields = ('event__title', 'name', 'email', 'message', 'subject')
    list_export = ["event", "submit_time", "subject", "name", "email", "telephone", "message", "is_member"]
    list_display = ('submit_time', 'event', 'name', 'email',)
    filterset_class = EventFilter
    edit_handler = ObjectList(EventRegistration.panels, base_form_class=EventRegistrationAdminForm)
