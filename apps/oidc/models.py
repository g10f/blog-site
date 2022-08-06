import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class RoleGroup(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='oidc_group')
    role = models.CharField(_("role"), max_length=512)
    is_staff = models.BooleanField(_("staff status"), default=False, help_text=_("Designates whether the user can log into this admin site."), )
    is_superuser = models.BooleanField(_("superuser status"), default=False,
                                       help_text=_("Designates that this user has all permissions without explicitly assigning them."), )


def is_staff(roles):
    return RoleGroup.objects.filter(role__in=roles, is_staff=True).exists()


def is_superuser(roles):
    return RoleGroup.objects.filter(role__in=roles, is_superuser=True).exists()


class UserProfile(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name='oidc_userprofile')
    subject = models.CharField(_("subject"), unique=True, max_length=254)

    def update_groups(self, roles):
        desired_groups = set(RoleGroup.objects.filter(role__in=roles).values_list('group__name', flat=True))
        current_groups = set(RoleGroup.objects.filter(group__in=self.user.groups.all()).values_list('group__name', flat=True))

        remove_groups = current_groups - desired_groups
        if remove_groups:
            groups = Group.objects.filter(name__in=remove_groups)
            self.user.groups.remove(*groups)

        add_groups = desired_groups - current_groups
        if add_groups:
            groups = Group.objects.filter(name__in=add_groups)
            self.user.groups.add(*groups)
