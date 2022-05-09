import logging

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class UserProfile(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name='core_userprofile')
    roles = models.CharField(_("roles"), max_length=512)
    subject = models.CharField(_("subject"),  unique=True, max_length=254)

