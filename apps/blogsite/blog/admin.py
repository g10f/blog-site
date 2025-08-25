import django_filters
from django.contrib import admin
from wagtail.admin.filters import WagtailFilterSet
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import EventRegistration, EventPage


class EventFilter(WagtailFilterSet):
    event = django_filters.ModelChoiceFilter(queryset=EventPage.objects.filter(event__isnull=False).distinct().order_by('-start_date'))

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


class EventRegistrationAdmin(SnippetViewSet):
    icon = 'mail'
    model = EventRegistration
    add_to_admin_menu = True
    menu_icon = 'mail'
    search_fields = ('event__title', 'name', 'email', 'message', 'subject')
    list_export = ["event", "submit_time", "subject", "name", "email", "telephone", "message", "is_member"]
    list_display = ('submit_time', 'event', 'name', 'email',)
    filterset_class = EventFilter

    @admin.display
    def event(self, obj):
        return f"{obj.page}-{obj.page.specific.start_date.date()}"
