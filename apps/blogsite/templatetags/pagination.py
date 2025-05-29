from django.template import Library
from django.utils.html import format_html
from django.utils.safestring import mark_safe


register = Library()

DOT = '.'
PAGE_VAR = 'page'


@register.simple_tag
def paginator_number(page, i):
    """
    Generates an individual page index link in a paginated list.
    """
    if i == DOT:
        return mark_safe('<li class="page-item disabled"><span class="page-link">&hellip;</span></li>')
    elif i == page.number - 1:
        return format_html('<li class="page-item"><a accesskey="p" class="page-link" href="{0}" >{1}</a></li>', f"?{PAGE_VAR}={i}", i)
    elif i == page.number:
        return format_html('<li class="page-item active" aria-current="page"><span class="page-link">{0}</span></li>', i)
    elif i == page.number + 1:
        return format_html('<li class="page-item"><a accesskey="n" class="page-link" href="{0}" >{1}</a></li>', f"?{PAGE_VAR}={i}", i)
    else:
        return format_html('<li class="page-item"><a class="page-link" href="{0}" >{1}</a></li>', f"?{PAGE_VAR}={i}", i)


@register.inclusion_tag('includes/pagination.html')
def pagination(page):
    """
    Generates the series of links to the pages in a paginated list.
    """
    paginator, page_num = page.paginator, page.number

    pagination_required = (paginator.num_pages > 1)
    if not pagination_required:
        page_range = []
    else:
        on_each_side = 1
        on_ends = 1

        # If there are 2 * (ON_EACH_SIDE + ON_ENDS) or fewer pages, display links to every page.
        # Otherwise, do some fancy
        num_items = 2 * (on_each_side + on_ends + 1) + 1
        if paginator.num_pages <= num_items:
            page_range = range(1, paginator.num_pages + 1)
        else:
            # Insert "smart" pagination links, so that there are always ON_ENDS
            # links at either end of the list of pages, and there are always
            # ON_EACH_SIDE links at either end of the "current page" link.
            page_range = []
            if page_num > (on_each_side + on_ends + 2):
                page_range.extend(range(1, on_ends + 1))
                page_range.append(DOT)
                if page_num > paginator.num_pages - on_each_side - on_ends - 1:
                    extra = page_num - paginator.num_pages + on_each_side + on_ends + 1
                    page_range.extend(range(page_num - on_each_side - extra, page_num))
                else:
                    page_range.extend(range(page_num - on_each_side, page_num))
            else:
                page_range.extend(range(1, page_num))
            if page_num < (paginator.num_pages - on_each_side - on_ends - 1):
                page_range.extend(range(page_num, page_num + num_items - len(page_range) - 2))
                page_range.append(DOT)
                page_range.extend(range(paginator.num_pages - on_ends + 1, paginator.num_pages + 1))
            else:
                page_range.extend(range(page_num, paginator.num_pages + 1))

    return {
        'page': page,
        'pagination_required': pagination_required,
        'page_range': page_range,
    }
