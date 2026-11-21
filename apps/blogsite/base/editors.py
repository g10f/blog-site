"""
The editors of a site: two Wagtail groups per site, so that a beginner has as few choices as possible and can
change and add content without an explanation, while an editor who wants more gets it with a second role.

"<group>" (role "<role>"), the editors:
- change and publish every page of the site (there is no moderation, the editors publish themselves),
- add pages only below the blog index pages; as these allow blog posts only, "add page" opens the form of a
  blog post directly, without a choice of page types,
- images and documents in the collection of the site, people (authors) of the site.

"<group> erweitert" (role "<role>-erweitert"), the advanced editors: the same, and they may add pages of every
type anywhere in the site.

Deleting and unpublishing follow the right to add (wagtail_hooks.py): whoever may not add a page at its place may
not delete or unpublish it either, so an editor can't remove the imprint, an advanced editor can, and only a
superuser can take the home page of a site offline.

Everything else (logo, footer, settings, events, registrations) is not given to editors; the operator adds it to
a group by hand where it is needed. The groups get their members from the roles in Keycloak with the same name
as their RoleGroups (oidc), at every login.
"""
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from wagtail.models import Collection, GroupCollectionPermission, GroupPagePermission, Page

from blogsite.blog.models import BlogIndexPage
from oidc.models import RoleGroup

SITE_ROOT_PAGE_PERMISSIONS = ["change_page", "publish_page"]
ADVANCED_SITE_ROOT_PAGE_PERMISSIONS = ["add_page", "change_page", "publish_page"]
BLOG_INDEX_PAGE_PERMISSIONS = ["add_page"]
COLLECTION_PERMISSIONS = ["add_image", "change_image", "choose_image",
                          "add_document", "change_document", "choose_document"]
SHARED_COLLECTION_PERMISSIONS = ["choose_image", "choose_document"]
MODEL_PERMISSIONS = ["wagtailadmin.access_admin", "base.add_people", "base.change_people", "base.delete_people"]

ADVANCED_GROUP_SUFFIX = " erweitert"
ADVANCED_ROLE_SUFFIX = "-erweitert"


def get_permission(app_label_codename):
    app_label, codename = app_label_codename.split(".")
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


def get_page_permission(codename):
    return Permission.objects.get(content_type__app_label="wagtailcore", codename=codename)


def get_collection_permission(codename):
    app_label = "wagtailimages" if codename.endswith("_image") else "wagtaildocs"
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


def blog_index_pages(site):
    # exact type: an EventIndexPage (a subclass) would allow event pages
    return Page.objects.descendant_of(site.root_page, inclusive=True).exact_type(BlogIndexPage)


def editor_groups(group_name, role):
    """(group name, role) of the editors and of the advanced editors."""
    return [(group_name, role), (group_name + ADVANCED_GROUP_SUFFIX, role + ADVANCED_ROLE_SUFFIX)]


def check_editor_groups(group_name, role):
    """Raises ValueError if a role of the two groups already belongs to another group."""
    for name, group_role in editor_groups(group_name, role):
        other = RoleGroup.objects.filter(role=group_role).exclude(group__name=name).select_related("group").first()
        if other is not None:
            raise ValueError(f"The role {group_role} already belongs to the group '{other.group}'.")


@transaction.atomic
def set_editor_groups(site, group_name, role, collection, shared_collections=()):
    """
    Creates or updates the two editor groups of a site and sets their rights to exactly the ones above. This is a
    reset: rights a group had before and that are not in this list (e.g. given by hand) are removed, and listed as
    "REMOVED" in what is returned. Run it again after adding a blog index page, so that the editors may add posts
    there too. Returns a list of what was done.
    """
    blog_indexes = list(blog_index_pages(site))
    if not blog_indexes:
        raise ValueError(f"The site {site.hostname} has no blog index page, its editors could not add anything.")
    check_editor_groups(group_name, role)

    done = []
    (name, group_role), (advanced_name, advanced_role) = editor_groups(group_name, role)
    done += set_group(name, group_role, site, SITE_ROOT_PAGE_PERMISSIONS, blog_indexes, collection,
                      shared_collections)
    done += set_group(advanced_name, advanced_role, site, ADVANCED_SITE_ROOT_PAGE_PERMISSIONS, blog_indexes,
                      collection, shared_collections)
    return done


def set_group(group_name, role, site, root_permissions, blog_indexes, collection, shared_collections):
    group, created = Group.objects.get_or_create(name=group_name)
    done = [f"group '{group_name}' {'created' if created else 'updated'}, role {role}"]
    rights_before = describe_rights(group)
    RoleGroup.objects.update_or_create(group=group, defaults={"role": role, "is_staff": False, "is_superuser": False})

    GroupPagePermission.objects.filter(group=group).delete()
    for codename in root_permissions:
        GroupPagePermission.objects.create(group=group, page=site.root_page, permission=get_page_permission(codename))
    done.append(f"  {', '.join(root_permissions)} on '{site.root_page.title}'")
    if "add_page" not in root_permissions:
        for page in blog_indexes:
            for codename in BLOG_INDEX_PAGE_PERMISSIONS:
                GroupPagePermission.objects.create(group=group, page=page, permission=get_page_permission(codename))
            done.append(f"  {', '.join(BLOG_INDEX_PAGE_PERMISSIONS)} on '{page.title}'")

    GroupCollectionPermission.objects.filter(group=group).delete()
    for codename in COLLECTION_PERMISSIONS:
        GroupCollectionPermission.objects.create(group=group, collection=collection,
                                                 permission=get_collection_permission(codename))
    done.append(f"  images and documents in the collection '{collection.name}'")
    for shared in shared_collections:
        for codename in SHARED_COLLECTION_PERMISSIONS:
            GroupCollectionPermission.objects.create(group=group, collection=shared,
                                                     permission=get_collection_permission(codename))
        done.append(f"  choose images and documents from the collection '{shared.name}'")

    group.permissions.set([get_permission(name) for name in MODEL_PERMISSIONS])
    done.append(f"  model permissions: {', '.join(MODEL_PERMISSIONS)}")

    # rights given to the group by hand are gone now: say which, so that nothing is lost unnoticed
    for right in sorted(rights_before - describe_rights(group)):
        done.append(f"  REMOVED: {right}")
    return done


def describe_rights(group):
    """All rights of a group as readable lines, to compare them before and after set_editor_groups()."""
    rights = {f"{p.permission.codename} on page '{p.page.title}' ({p.page_id})"
              for p in group.page_permissions.select_related("page", "permission")}
    rights |= {f"{p.permission.codename} in collection '{p.collection.name}'"
               for p in group.collection_permissions.select_related("collection", "permission")}
    rights |= {f"{p.content_type.app_label}.{p.codename}" for p in group.permissions.select_related("content_type")}
    return rights


def get_or_create_collection(name):
    """
    The collection with this name, wherever it is in the tree ("Root" is the root collection); a new one directly
    below the root collection if there is none.

    "Root" gives the editors all images and documents of the instance, also those of collections added later:
    only for an instance with one site. With a second site, give each site a collection of its own.
    """
    existing = list(Collection.objects.filter(name=name))
    if len(existing) > 1:
        raise ValueError(f"There are {len(existing)} collections named '{name}', rename all but one.")
    if existing:
        return existing[0]
    return Collection.get_first_root_node().add_child(name=name)
