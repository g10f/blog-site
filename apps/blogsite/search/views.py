from django.contrib.sites.shortcuts import get_current_site
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from wagtail.models import Page, Site
from wagtail.search.models import Query


def search(request):
    search_query = request.GET.get('q', None)
    page = request.GET.get('page', 1)
    site = Site.find_for_request(request)

    # Search
    if search_query:
        search_results = Page.objects.live().in_site(site).search(search_query)
        query = Query.get(search_query)

        # Record hit
        query.add_hit()
    else:
        search_results = Page.objects.none()

    # Pagination
    paginator = Paginator(search_results, 10)
    try:
        search_results = paginator.page(page)
    except PageNotAnInteger:
        search_results = paginator.page(1)
    except EmptyPage:
        search_results = paginator.page(paginator.num_pages)

    return TemplateResponse(request, 'search/search_results.html', {
        'title': _('Search results'),
        'search_query': search_query,
        'search_results': search_results
    })
