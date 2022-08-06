from django.contrib.auth.hashers import make_password
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from .models import UserProfile, RoleGroup, is_superuser, is_staff


class AuthenticationBackend(OIDCAuthenticationBackend):
    def get_userinfo(self, access_token, id_token, payload):
        return payload

    def verify_claims(self, claims):
        # verify that the user has at least on Group
        return RoleGroup.objects.filter(role__in=claims.get('roles', '').split()).exists()

    def get_username(self, claims):
        return claims['name']

    def filter_users_by_claims(self, claims):
        """Return all users matching the specified email."""
        sub = claims.get('sub')
        if not sub:
            return self.UserModel.objects.none()

        return self.UserModel.objects.filter(oidc_userprofile__subject=sub)

    def create_user(self, claims):
        email = claims.get('email')
        sub = claims.get('sub')
        first_name = claims.get('given_name', '')
        last_name = claims.get('family_name', '')
        username = self.get_username(claims)
        roles = claims.get('roles', '').split()

        unusable_password = make_password(None)
        user = self.UserModel.objects.get_or_create(
            defaults={'first_name': first_name, 'last_name': last_name, 'email': email,
                      'is_staff': is_staff(roles), 'is_superuser': is_superuser(roles), 'password': unusable_password},
            username=username)[0]
        user_profile = UserProfile(user=user, subject=sub)
        user_profile.save()
        user_profile.update_groups(roles)
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

        roles = claims.get('roles', '').split()
        user.oidc_userprofile.update_groups(roles)

        update_user('email', claims.get('email'))
        update_user('first_name', claims.get('given_name', ''))
        update_user('last_name', claims.get('family_name', ''))
        update_user('is_staff', is_staff(roles))
        update_user('is_superuser', is_superuser(roles))
        save_user()
        return user
