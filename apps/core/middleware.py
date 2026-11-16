from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware


# from https://github.com/cfpb/consumerfinance.gov/blob/main/cfgov/core/middleware.py
class PathBasedCsrfViewMiddleware(CsrfViewMiddleware):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        csrf_required_paths = getattr(settings, "CSRF_REQUIRED_PATHS", None)

        # If CSRF_REQUIRED_PATHS is not configured, apply the CSRF middleware
        # to everything. Otherwise only apply it if the request path matches
        # the configured paths.
        if csrf_required_paths is not None and not any(request.path.startswith(path) for path in csrf_required_paths):
            return None

        return super().process_view(request, callback, callback_args, callback_kwargs)


class EditorCookieMiddleware:
    """Marks the browser of a logged-in editor with a cookie, for the web server in front of the cache.

    Public pages are answered from a cache and without cookies. Only an editor has to get past the cache, so that
    his pages show the Wagtail userbar. The session cookie can't tell the web server who that is: an anonymous
    visitor has one as well after opening the login page. So this cookie exists exactly as long as the user is
    logged in and may use the Wagtail admin:
    - it is set on a request to the admin by such a user (the login redirects there),
    - it is deleted by the first request that carries it without such a login (logged out, session expired,
      cookie made up).

    The cookie gives no rights, they come from the session alone. A browser with a made-up cookie gets one
    answer past the cache and loses the cookie with it. A program that keeps sending it gets every answer past
    the cache, like anybody could on the separate admin domain before; the request limit of the web server
    applies to it.

    Has to come after AuthenticationMiddleware in MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        cookie_name = settings.EDITOR_COOKIE_NAME
        has_cookie = cookie_name in request.COOKIES
        is_admin_request = request.path.startswith(settings.EDITOR_COOKIE_SET_PATHS)
        if not has_cookie and not is_admin_request:
            # The normal case, a visitor on a public page: request.user is not touched, because reading the
            # session adds "Vary: Cookie" to the response.
            return response

        user = getattr(request, "user", None)
        is_editor = user is not None and user.is_authenticated and user.has_perm("wagtailadmin.access_admin")
        if is_editor and not has_cookie:
            response.set_cookie(
                cookie_name,
                "1",
                # as long as the session cookie; when it is gone earlier, the next request to the admin sets it again
                max_age=settings.SESSION_COOKIE_AGE,
                secure=request.is_secure(),
                httponly=True,
                samesite="Lax",
            )
        elif has_cookie and not is_editor:
            response.delete_cookie(cookie_name)
        return response
