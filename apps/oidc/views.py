from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, resolve_url
from wagtail.admin.views import account

from core.http import update_url


class OIDCLoginView(account.LoginView):
    """
    automatically redirect to OIDC Provider.
    Can be disabled with noredir=1 URL param.
    """

    def get(self, request, *args, **kwargs):
        if not getattr(settings, 'OIDC_OP_AUTHORIZATION_ENDPOINT', None) \
            or ("noredir" in request.GET and request.GET["noredir"] == "1") \
            or (self.request.user.is_authenticated and self.request.user.has_perm("wagtailadmin.access_admin")):
            return super().get(request, *args, **kwargs)
        else:
            return redirect('oidc_authentication_init')


class OIDCLogoutView(account.LogoutView):
    def dispatch(self, request, *args, **kwargs):
        # if id_token is in session (OIDC_STORE_ID_TOKEN = True) and OIDC_OP_LOGOUT_URL_METHOD configured
        # we redirect to OIDC Provider
        id_token_hint = request.session.get("oidc_id_token")
        logout_redirect_url = getattr(settings, 'OIDC_OP_LOGOUT_URL_METHOD', None)
        if not id_token_hint or not logout_redirect_url:
            return super().dispatch(request, *args, **kwargs)
        else:
            logout(request)
            post_logout_redirect_uri = request.build_absolute_uri(resolve_url(settings.LOGIN_REDIRECT_URL))
            logout_url = update_url(logout_redirect_url,
                                    {'id_token_hint': id_token_hint, 'post_logout_redirect_uri': post_logout_redirect_uri})
            return HttpResponseRedirect(logout_url)
