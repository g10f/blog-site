from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.contrib.sitemaps.views import sitemap
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from .search import views as search_views

urlpatterns = [
    path('sitemap.xml', sitemap),
    path('oidc/', include('mozilla_django_oidc.urls')),
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
# These will be available under a language code prefix. For example /en/search/
# urlpatterns += i18n_patterns(
#     path('search/', search_views.search, name='search'),
#     path("", include(wagtail_urls)),
# )
urlpatterns += [
    path('search/', search_views.search, name='search'),
    path('', include(wagtail_urls)),
]
