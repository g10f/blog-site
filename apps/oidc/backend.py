import logging

from django.contrib.auth.hashers import make_password
from django.db import transaction
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from .models import UserProfile, RoleGroup, is_superuser, is_staff

logger = logging.getLogger(__name__)


def get_roles(claims):
    roles = claims.get('roles')
    if isinstance(roles, str):
        return roles.split()
    elif isinstance(roles, (tuple, list)):
        return roles

    return []


class AuthenticationBackend(OIDCAuthenticationBackend):
    def get_userinfo(self, access_token, id_token, payload):
        return payload

    def verify_claims(self, claims):
        # verify that the user has at least on Group
        return RoleGroup.objects.filter(role__in=get_roles(claims)).exists()

    def get_username(self, claims):
        # "preferred_username" is the login name, which is unique at the provider. "name" is the display name
        # ("Peter Müller"), which two people can share; it is only used for a provider without the other claim.
        # None without both; create_user refuses the login then.
        return claims.get('preferred_username') or claims.get('name')

    def filter_users_by_claims(self, claims):
        """Return all users matching the specified email."""
        sub = claims.get('sub')
        if not sub:
            return self.UserModel.objects.none()

        return self.UserModel.objects.filter(oidc_userprofile__subject=sub)

    def create_user(self, claims):
        """Called at the first login of a subject: create his user.

        An account that already has the username is never taken over, whether it is a local one (like the
        superuser "admin") or belongs to another subject: the login is refused (returning None makes
        mozilla-django-oidc treat the login as failed). The username is compared without case, Keycloak writes
        usernames in lower case. To give an existing account to a user of the provider, an administrator links
        it by hand: an "OIDC user profile" with the subject of the user, in the Django admin.
        """
        sub = claims.get('sub')
        username = self.get_username(claims)
        roles = get_roles(claims)

        max_length = self.UserModel._meta.get_field('username').max_length
        if not username or len(username) > max_length:
            # Without the scope "profile" Keycloak sends neither "preferred_username" nor "name" (OIDC_RP_SCOPES).
            logger.warning(
                "OIDC login refused: the subject %s has no username in the claims 'preferred_username' and 'name', "
                "or one with more than %s characters.", sub, max_length)
            return None

        if self.UserModel.objects.filter(username__iexact=username).exists():
            logger.warning(
                "OIDC login refused: the subject %s has the username %r, but there already is an account with "
                "this username. To give it to this user, add an OIDC user profile with the subject to the account.",
                sub, username)
            return None

        # All or nothing: a user never stays behind without his subject, he could not log in again.
        with transaction.atomic():
            user = self.UserModel.objects.create(
                username=username, email=claims.get('email') or '', first_name=claims.get('given_name', ''),
                last_name=claims.get('family_name', ''), is_staff=is_staff(roles), is_superuser=is_superuser(roles),
                password=make_password(None))
            UserProfile.objects.create(user=user, subject=sub)
            user.oidc_userprofile.update_groups(roles)
        return user

    def update_user(self, user, claims):
        def update_user(name, value):
            old_value = getattr(user, name)
            if old_value != value:
                setattr(user, name, value)
                setattr(user, '__changed', True)
            return user

        def save_user():
            if getattr(user, '__changed', False):
                user.save()

        roles = get_roles(claims)
        user.oidc_userprofile.update_groups(roles)

        # a provider without a mail address for the user: the field can't be NULL
        update_user('email', claims.get('email') or '')
        update_user('first_name', claims.get('given_name', ''))
        update_user('last_name', claims.get('family_name', ''))
        update_user('is_staff', is_staff(roles))
        update_user('is_superuser', is_superuser(roles))
        save_user()
        return user
