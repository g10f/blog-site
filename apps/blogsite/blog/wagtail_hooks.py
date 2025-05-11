from wagtail import hooks

from blogsite.blog.admin import EventRegistrationAdmin

@hooks.register("register_admin_viewset")
def register_viewset():
    return EventRegistrationAdmin()
