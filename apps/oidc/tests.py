from django.contrib.auth import get_user_model
from django.test import TestCase

from oidc.backend import AuthenticationBackend
from oidc.models import UserProfile

User = get_user_model()


def claims(sub, username, roles=("Editors",), **extra):
    return {"sub": sub, "preferred_username": username, "name": "Peter Müller", "email": f"{username}@example.com",
            "given_name": "Peter", "family_name": "Müller", "roles": list(roles), **extra}


class CreateUserTest(TestCase):
    """The RoleGroups "Editors", "Moderators" and "Superuser" come from the migration 0005."""

    def setUp(self):
        self.backend = AuthenticationBackend()

    def test_new_user_gets_the_preferred_username(self):
        user = self.backend.create_user(claims("sub-1", "pmueller"))
        self.assertEqual(user.username, "pmueller")
        self.assertEqual(user.oidc_userprofile.subject, "sub-1")
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Editors"])
        self.assertFalse(user.has_usable_password())

    def test_two_people_with_the_same_display_name_get_two_accounts(self):
        first = self.backend.create_user(claims("sub-1", "pmueller"))
        second = self.backend.create_user(claims("sub-2", "peter.mueller"))
        self.assertNotEqual(first.pk, second.pk)

    def test_name_is_the_username_without_preferred_username(self):
        without = claims("sub-1", "pmueller")
        del without["preferred_username"]
        self.assertEqual(self.backend.create_user(without).username, "Peter Müller")

    def test_local_account_is_not_taken_over(self):
        existing = User.objects.create_user("PMueller", password="x", is_superuser=True, is_staff=True)
        self.assertIsNone(self.backend.create_user(claims("sub-1", "pmueller", roles=("Superuser",))))
        existing.refresh_from_db()
        self.assertTrue(existing.is_superuser)
        self.assertTrue(existing.has_usable_password())
        self.assertEqual(UserProfile.objects.count(), 0)
        self.assertEqual(User.objects.count(), 1)

    def test_account_of_another_subject_is_not_taken_over(self):
        self.backend.create_user(claims("sub-1", "pmueller"))
        self.assertIsNone(self.backend.create_user(claims("sub-2", "PMUELLER")))
        self.assertEqual(UserProfile.objects.get(user__username="pmueller").subject, "sub-1")

    def test_account_linked_by_hand_is_found_by_the_subject(self):
        existing = User.objects.create_user("PMueller", password="x")
        UserProfile.objects.create(user=existing, subject="sub-1")
        found = self.backend.filter_users_by_claims(claims("sub-1", "pmueller"))
        self.assertEqual(list(found), [existing])
        user = self.backend.update_user(existing, claims("sub-1", "pmueller"))
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Editors"])

    def test_login_without_a_username_is_refused(self):
        without = claims("sub-1", "pmueller")
        del without["preferred_username"], without["name"]
        self.assertIsNone(self.backend.create_user(without))
        self.assertEqual(User.objects.count(), 0)

    def test_too_long_username_is_refused(self):
        self.assertIsNone(self.backend.create_user(claims("sub-1", "p" * 151)))
        self.assertEqual(User.objects.count(), 0)

    def test_user_without_mail_address(self):
        without = claims("sub-1", "pmueller")
        del without["email"]
        user = self.backend.create_user(without)
        self.assertEqual(user.email, "")
        self.assertEqual(self.backend.update_user(user, without).email, "")

    def test_second_login_finds_the_user_by_his_subject(self):
        user = self.backend.create_user(claims("sub-1", "pmueller"))
        # the username at the provider may differ by now, the subject counts
        found = self.backend.filter_users_by_claims(claims("sub-1", "other"))
        self.assertEqual(list(found), [user])

    def test_login_without_a_known_role_is_refused(self):
        self.assertFalse(self.backend.verify_claims(claims("sub-1", "pmueller", roles=("Unknown",))))
        self.assertTrue(self.backend.verify_claims(claims("sub-1", "pmueller")))
