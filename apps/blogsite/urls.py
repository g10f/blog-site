from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.contrib.sitemaps.views import sitemap
from wagtail.documents import urls as wagtaildocs_urls

from oidc.views import OIDCLoginView, OIDCLogoutView
from .search import views as search_views

urlpatterns = []

# add mozilla_django_oidc first, if configured
if getattr(settings, 'OIDC_OP_NAME', ''):
    urlpatterns += [
        path('oidc/', include('mozilla_django_oidc.urls')),
        path('admin/login/', OIDCLoginView.as_view(), name="wagtailadmin_login"),
        path('admin/logout/', OIDCLogoutView.as_view(), name="wagtailadmin_logout")
    ]

urlpatterns += [
    path('sitemap.xml', sitemap),
    path('django-admin/', admin.site.urls),
    path('admin/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'ico/favicon.ico'))]

# Translatable URLs
if settings.WAGTAIL_I18N_ENABLED:
    # These will be available under a language code prefix. For example /en/search/
    urlpatterns += i18n_patterns(
        path('search/', search_views.search, name='search'),
        path("", include(wagtail_urls)),
        prefix_default_language=False,
    )
else:
    urlpatterns += [
        path('search/', search_views.search, name='search'),
        path('', include(wagtail_urls)),
    ]
