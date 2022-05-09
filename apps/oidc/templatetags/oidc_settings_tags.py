from django import template
from django.conf import settings

register = template.Library()


# https://docs.djangoproject.com/en/3.2/howto/custom-template-tags/


@register.simple_tag()
def get_idp_name():
    return getattr(settings, 'OIDC_OP_NAME', "")
