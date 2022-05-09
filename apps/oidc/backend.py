from django.contrib.auth.models import Group
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.hashers import make_password
from .models import UserProfile


class MyOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    staff_roles = {'Staff', 'Superuser'}
    user_roles = {'Staff', 'Superuser'}
    superuser_role = 'Superuser'

    def get_userinfo(self, access_token, id_token, payload):
        return payload

    def verify_claims(self, claims):
        # verify that the user hs at least on of the self.user_roles
        existing_roles = set(claims.get('roles', '').split())
        return len(self.user_roles & existing_roles) > 0

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
        roles = claims.get('roles', '')
        username = self.get_username(claims)
        is_staff = len(set(roles.split()) & self.staff_roles) > 0
        is_superuser = self.superuser_role in roles.split()

        unusable_password = make_password(None)
        user = self.UserModel.objects.get_or_create(
            defaults={'first_name': first_name, 'last_name': last_name, 'email': email,
                      'is_staff': is_staff, 'is_superuser': is_superuser, 'password': unusable_password},
            username=username)[0]
        user_profile = UserProfile(user=user, roles=roles, subject=sub)
        user_profile.save()

        groups = set()
        for role in filter(lambda x: x != self.superuser_role, roles.split()):
            groups.add(Group.objects.get_or_create(name=role)[0])
        user.groups.add(*groups)
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

        roles = claims.get('roles', '')
        desired_roles = set(roles.split())
        current_roles = set(user.oidc_userprofile.roles.split())

        remove_groups = current_roles - desired_roles
        if remove_groups:
            groups = Group.objects.filter(name__in=remove_groups)
            user.groups.remove(*groups)

        add_groups = desired_roles - current_roles
        if add_groups:
            groups = set()
            for group_name in filter(lambda x: x not in self.superuser_roles, add_groups):
                groups.add(Group.objects.get_or_create(name=group_name)[0])
            user.groups.add(*groups)

        update_user('email', claims.get('email'))
        update_user('first_name', claims.get('given_name', ''))
        update_user('last_name', claims.get('family_name', ''))
        update_user('is_staff', len(set(roles.split()) & self.staff_roles) > 0)
        update_user('is_superuser', self.superuser_role in roles.split())
        save_user()
        return user
