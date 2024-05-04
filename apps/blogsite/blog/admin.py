from wagtail_modeladmin.options import ModelAdmin

from django.contrib import admin
from .models import EventRegistration


class EventRegistrationAdmin(ModelAdmin):
    model = EventRegistration
    menu_icon = 'mail'
    list_filter = ('event',)
    search_fields = ('event__title', 'name', 'email', 'message', 'subject')
    list_export = ["event", "submit_time", "subject", "name", "email", "telephone", "message", "is_member"]

    @admin.display
    def event(self, obj):
        return f"{obj.page}-{obj.page.specific.start_date.date()}"
