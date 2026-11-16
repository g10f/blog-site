from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

COOKIE = "editor"


@override_settings(ALLOWED_HOSTS=["testserver"])
class EditorCookieMiddlewareTest(TestCase):
    def setUp(self):
        self.editor = get_user_model().objects.create_user("editor", password="x")
        # the group "Editors" of Wagtail may use the admin
        self.editor.groups.add(Group.objects.get(name="Editors"))
        self.visitor = get_user_model().objects.create_user("visitor", password="x")

    def test_anonymous_visitor_gets_no_cookie(self):
        response = self.client.get("/admin/login/?noredir=1")
        self.assertNotIn(COOKIE, response.cookies)

    def test_public_page_of_a_visitor_does_not_read_the_session(self):
        # reading the session would add "Vary: Cookie", and the page could not be cached for everybody
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Cookie", response.headers.get("Vary", ""))
        self.assertEqual(len(response.cookies), 0)

    def test_editor_gets_the_cookie_in_the_admin(self):
        self.client.force_login(self.editor)
        response = self.client.get("/admin/")
        cookie = response.cookies[COOKIE]
        self.assertEqual(cookie.value, "1")
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["max-age"], 1209600)

    def test_cookie_is_deleted_when_the_user_lost_the_admin_access(self):
        self.client.force_login(self.editor)
        self.client.cookies[COOKIE] = "1"
        self.editor.groups.clear()
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.cookies[COOKIE]["max-age"], 0)

    def test_editor_gets_no_cookie_on_a_public_page(self):
        # the cookie is only set in the admin, so that public pages don't read the session
        self.client.force_login(self.editor)
        response = self.client.get("/sitemap.xml")
        self.assertNotIn(COOKIE, response.cookies)

    def test_user_without_admin_access_gets_no_cookie(self):
        self.client.force_login(self.visitor)
        response = self.client.get("/admin/")
        self.assertNotIn(COOKIE, response.cookies)

    def test_cookie_is_kept_while_logged_in(self):
        self.client.force_login(self.editor)
        self.client.cookies[COOKIE] = "1"
        response = self.client.get("/sitemap.xml")
        self.assertNotIn(COOKIE, response.cookies)

    def test_made_up_cookie_is_deleted(self):
        self.client.cookies[COOKIE] = "1"
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.cookies[COOKIE].value, "")
        self.assertEqual(response.cookies[COOKIE]["max-age"], 0)

    def test_cookie_is_deleted_by_the_logout(self):
        self.client.force_login(self.editor)
        self.client.get("/admin/")
        self.assertEqual(self.client.cookies[COOKIE].value, "1")
        response = self.client.post("/admin/logout/")
        self.assertEqual(response.cookies[COOKIE]["max-age"], 0)
