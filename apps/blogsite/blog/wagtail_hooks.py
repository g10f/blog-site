from wagtail_modeladmin.options import modeladmin_register

from blogsite.blog.admin import EventRegistrationAdmin

modeladmin_register(EventRegistrationAdmin)
