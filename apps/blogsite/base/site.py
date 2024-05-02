from wagtail.permissions import page_permission_policy


def get_sites(user):
    pages = set(page_permission_policy.instances_with_direct_explore_permission(user))
    if len(pages) == 1:
        root = next(iter(pages))
        if root.is_root():
            pages = root.get_children()

    sites = {page.get_site() for page in pages if page.get_site() is not None}
    return sites
