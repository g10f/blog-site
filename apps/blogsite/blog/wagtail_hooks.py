from wagtail_modeladmin.options import ModelAdmin, modeladmin_register

from blogsite.blog.models import EventRegistration
from django.contrib import admin


class EventRegistrationAdmin(ModelAdmin):
    # These stub classes allow us to put various models into the custom "Wagtail Bakery" menu item
    # rather than under the default Snippets section.
    model = EventRegistration
    menu_icon = 'mail'
    list_display = ('submit_time', 'event', 'name', 'email')
    list_filter = ('event', )
    search_fields = ('event', 'name', 'email')
    @admin.display
    def event(self, obj):
        return f"{obj.page}-{obj.page.specific.start_date.date()}"


modeladmin_register(EventRegistrationAdmin)
