import logging
import re
import urllib.parse
from datetime import timedelta
from functools import partial

import wagtail
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import Tag, TaggedItemBase
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.contrib.frontend_cache.utils import PurgeBatch
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import StreamField
from wagtail.models import Page, Orderable
from wagtail.search import index
from wagtail.signals import page_published, post_page_move

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from ..base.blocks import BaseStreamBlock
from ..base.models import HomePage, get_cached_path

logger = logging.getLogger(__name__)

phone_re = re.compile(
    r'^(\+\d{1,3})?' + r'((-?\d+)|(\s?\(\d+\)\s?)|\s?\d+){1,9}$'
)
validate_phone = RegexValidator(phone_re, _("Enter a valid phone number i.e. +49 (531) 123456"), 'invalid')


class BlogPeopleRelationship(Orderable, models.Model):
    page = ParentalKey('BlogPage', related_name='blog_person_relationship', on_delete=models.CASCADE)
    people = models.ForeignKey('base.People', related_name='person_blog_relationship', on_delete=models.CASCADE)
    panels = [
        FieldPanel('people')
    ]


class EventSpeakerRelationship(Orderable, models.Model):
    page = ParentalKey('EventPage', related_name='event_speaker_relationship', on_delete=models.CASCADE)
    speaker = models.ForeignKey('base.Speaker', related_name='event_speaker_relationship', on_delete=models.CASCADE)
    panels = [
        FieldPanel('speaker')
    ]


class BlogPageTag(TaggedItemBase):
    """
    This model allows us to create a many-to-many relationship between
    the BlogPage object and tags. There's a longer guide on using it at
    https://docs.wagtail.io/en/latest/reference/pages/model_recipes.html#tagging
    """
    content_object = ParentalKey('BlogPage', related_name='tagged_items', on_delete=models.CASCADE)


class AuthorPanel(InlinePanel):
    def on_model_bound(self):
        super().on_model_bound()


class BlogPage(Page):
    """
    A Blog Page

    We access the People object with an inline panel that references the
    ParentalKey's related_name in BlogPeopleRelationship. More docs:
    https://docs.wagtail.io/en/latest/topics/pages.html#inline-models
    """
    intro_template = 'blog/_introduction.html'
    introduction = models.TextField(_('introduction'), help_text='Text to describe the page', blank=True)
    image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text='Landscape mode only; horizontal width between 1000px and 3000px.'
    )
    body = StreamField(BaseStreamBlock(), verbose_name=_("page body"), blank=True, use_json_field=True)
    subtitle = models.CharField(_('subtitle'), blank=True, max_length=255)
    tags = ClusterTaggableManager(through=BlogPageTag, blank=True)
    date_published = models.DateField(_("date article published"), default=timezone.now)

    content_panels = Page.content_panels + [
        FieldPanel('subtitle'),
        FieldPanel('introduction'),
        FieldPanel('image'),
        FieldPanel('body'),
        FieldPanel('date_published'),
        AuthorPanel(
            'blog_person_relationship', label="Author(s)",
            panels=None, min_num=1),
        FieldPanel('tags'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('subtitle'),
        index.SearchField('introduction'),
        index.SearchField('body'),
    ]
    tag = None

    def authors(self):
        """
        Returns the BlogPage's related People. Again note that we are using
        the ParentalKey's related_name from the BlogPeopleRelationship model
        to access these objects. This allows us to access the People objects
        with a loop on the template. If we tried to access the blog_person_
        relationship directly we'd print `blog.BlogPeopleRelationship.None`
        """
        authors = [
            n.people for n in self.blog_person_relationship.all()
        ]

        return authors

    @property
    def get_tags(self):
        """
        Similar to the authors function above we're returning all the tags that
        are related to the blog post into a list we can access on the template.
        We're additionally adding a URL to access BlogPage objects with that tag
        """
        tags = self.tags.all()
        for tag in tags:
            tag.url = urllib.parse.urljoin(self.get_parent().get_url_parts()[2], f'tags/{tag.slug}/')
        return tags

    def get_cached_paths(self):
        # Yield the main URL
        yield '/'

        # make sure all pages are purged
        for tag in self.tags.all():
            yield f'/?tag={tag.slug}'

    # Specifies parent to BlogPage as being BlogIndexPages
    parent_page_types = ['BlogIndexPage']

    # Specifies what content types can exist as children of BlogPage.
    # Empty list means that no child content types are allowed.
    subpage_types = []

    def serve(self, request, *args, **kwargs):
        tag = request.GET.get('tag')
        if tag:
            try:
                self.tag = Tag.objects.get(slug=request.GET.get('tag'))
            except Tag.DoesNotExist:
                msg = _('There is no tag "%(tag)s".') % {'tag': tag}
                messages.add_message(request, messages.INFO, msg)
                logger.warning(f'tag {tag} does not exist')

        return super().serve(request, *args, **kwargs)

    # unklar ob das nötig ist https://docs.wagtail.org/en/stable/releases/4.0.html#changes-to-page-serve-and-page-serve-preview-methods
    # def serve_preview(self, request, mode_name):
    #     return self.serve(request)

    def get_siblings(self, inclusive=True):
        """
        Returns a  BlogPage queryset instead of Page queryset, so that we can filter by tag.
        """
        return BlogPage.objects.sibling_of(self, inclusive)

    def _first_filtered_by_tag(self, func):
        qs = func().live()
        if self.tag:
            qs = qs.filter(tags=self.tag)
        return qs.first()

    @property
    def next(self):
        return self._first_filtered_by_tag(self.get_next_siblings)

    @property
    def previous(self):
        return self._first_filtered_by_tag(self.get_prev_siblings)


def _now_plus_120_minutes():
    return timezone.now() + timedelta(minutes=120)


class EventPage(BlogPage):
    """
    An Event Page

    We access the Speaker object with an inline panel that references the
    ParentalKey's related_name in EventSpeakerRelationship. More docs:
    https://docs.wagtail.io/en/latest/topics/pages.html#inline-models
    """
    intro_template = 'blog/_event_introduction.html'
    parent_page_types = ['EventIndexPage', 'BlogIndexPage']
    start_date = models.DateTimeField(_('start date'), default=timezone.now)
    end_date = models.DateTimeField(_('end date'), default=_now_plus_120_minutes)
    location = models.TextField(_('location'), blank=True)
    min_participants = models.IntegerField(_('minimum number of participants'), blank=True, null=True)
    max_participants = models.IntegerField(_('maximum number of participants'), blank=True, null=True)
    price = models.DecimalField(_('Price'), max_digits=6, decimal_places=2, blank=True, null=True)
    price_reduced = models.DecimalField(_('reduced Price'), max_digits=6, decimal_places=2, blank=True, null=True)
    is_registration_open = models.BooleanField(_('is registration open'), default=True)
    registration_end_date = models.DateTimeField(_('end date for registration'), blank=True, null=True)
    registration_email = models.EmailField(_("email address for registration"), blank=True)
    registration_phone_number = models.CharField(_("phone number for registration"), blank=True, max_length=30, validators=[validate_phone])
    is_booked_up = models.BooleanField(_('is booked up'), default=False)
    additional_infos = wagtail.fields.RichTextField(_('additional infos'), blank=True, help_text="Write additional information's", null=True)

    content_panels = Page.content_panels + [
        FieldPanel('subtitle'),
        FieldPanel('introduction'),
        FieldPanel('image'),
        InlinePanel(
            "event_speaker_relationship",
            heading=_("speakers"),
            label=_("speaker"),
            panels=None,
            min_num=0,
        ),
        FieldPanel('start_date'),
        FieldPanel('end_date'),
        FieldPanel('location'),
        FieldPanel('min_participants'),
        FieldPanel('max_participants'),
        FieldPanel('price'),
        FieldPanel('price_reduced'),
        FieldPanel('is_registration_open'),
        FieldPanel('registration_end_date'),
        FieldPanel('registration_email'),
        FieldPanel('registration_phone_number'),
        FieldPanel('is_booked_up'),
        FieldPanel('additional_infos'),
        FieldPanel('body'),
        FieldPanel('date_published'),
        AuthorPanel(
            'blog_person_relationship', label=_("authors"),
            panels=None, min_num=0),
        FieldPanel('tags'),
    ]

    def speakers(self):
        speakers = [
            n.speaker for n in self.event_speaker_relationship.all()
        ]

        return speakers

    @property
    def is_registration_expired(self):
        if self.registration_end_date and now() > self.registration_end_date:
            return True
        if now() > self.start_date:
            return True
        return False

    def get_siblings(self, inclusive=True):
        # Overwrite BlogPage.get_siblings that we can order by start_date.
        return EventPage.objects.sibling_of(self, inclusive)

    def get_next_siblings(self, inclusive=False):
        # Order by start_date
        return self.get_siblings(inclusive).filter(start_date__gte=self.start_date).order_by("start_date")

    def get_prev_siblings(self, inclusive=False):
        # Order by -start_date
        return (
            self.get_siblings(inclusive).filter(start_date__lte=self.start_date).order_by("-start_date")
        )


class BlogIndexPage(RoutablePageMixin, Page):
    """
    Index page for blogs.
    We need to alter the page model's context to return the child page objects,
    the BlogPage objects, so that it works as an index page

    RoutablePageMixin is used to allow for a custom sub-URL for the tag views
    defined above.
    """
    introduction = models.TextField(
        help_text=_('Text to describe the page'),
        blank=True)
    image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text='Landscape mode only; horizontal width between 1000px and 3000px.'
    )

    content_panels = Page.content_panels + [
        FieldPanel('introduction'),
        FieldPanel('image'),
    ]

    # Specifies that only BlogPage objects can live under this index page
    subpage_types = ['BlogPage']

    # Defines a method to access the children of the page (e.g. BlogPage
    # objects). On the demo site we use this on the HomePage
    def children(self, num_pages=3):
        return self.get_children().specific().live().order_by('-path')[:num_pages]
        # return BlogPage.objects.live().descendant_of(self).order_by('-date_published')

    # Pagination for the index page. We use the `django.core.paginator` as any
    # standard Django app would, but the difference here being we have it as a
    # method on the model rather than within a view function
    def paginate(self, request, posts):
        page = request.GET.get('page')
        paginator = Paginator(posts, settings.BLOGSITE_PAGE_SIZE)
        try:
            pages = paginator.page(page)
        except PageNotAnInteger:
            pages = paginator.page(1)
        except EmptyPage:
            pages = paginator.page(paginator.num_pages)
        return pages

    # Overrides the context to list all child items, that are live, by the
    # date that they were published
    # https://docs.wagtail.io/en/latest/getting_started/tutorial.html#overriding-context
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context['posts'] = self.paginate(request, self.get_posts())
        return context

    # This defines a Custom view that utilizes Tags. This view will return all
    # related BlogPages for a given Tag or redirect back to the BlogIndexPage.
    # More information on RoutablePages is at
    # https://docs.wagtail.io/en/latest/reference/contrib/routablepage.html
    @path('tags/', name='tag_archive')
    @path('tags/<tag>/', name='tag_archive')
    def tag_archive(self, request, tag=None):
        try:
            tag = Tag.objects.get(slug=tag)
        except Tag.DoesNotExist:
            if tag:
                msg = _('There is no tag "%(tag)s".') % {'tag': tag}
                messages.add_message(request, messages.INFO, msg)
            return redirect(self.url)

        posts = self.paginate(request, self.get_posts(tag=tag))
        context = super(BlogIndexPage, self).get_context(request)
        context['tag'] = tag
        context['posts'] = posts
        return render(request, 'blog/blog_index_page.html', context)

    def get_cached_paths(self):
        return get_cached_path(
            items=Tag.objects.filter(blog_blogpagetag_items__isnull=False).distinct(),
            item_attribute='slug',
            reverse_subpage=partial(self.reverse_subpage, 'tag_archive'),
            filter_method=self.get_posts)

    # Returns the child BlogPage objects for this BlogPageIndex.
    # If a tag is used then it will filter the posts by tag.
    def get_posts(self, tag=None):
        posts = BlogPage.objects.live().descendant_of(self).order_by('-path')
        if tag:
            posts = posts.filter(tags=tag)
        return posts

    # Returns the list of Tags for all child posts of this BlogPage.
    def get_child_tags(self):
        tags = []
        for post in self.get_posts():
            # Not tags.append() because we don't want a list of lists
            tags += post.get_tags
        tags = sorted(set(tags))
        return tags


class EventIndexPage(BlogIndexPage):
    subpage_types = ['EventPage']

    # Returns the child BlogPage objects for this BlogPageIndex.
    # If a tag is used then it will filter the posts by tag.
    def get_posts(self, tag=None):
        posts = EventPage.objects.live().descendant_of(self).order_by('-start_date')
        if tag:
            posts = posts.filter(tags=tag)
        return posts

    # Defines a method to access the children of the page (e.g. BlogPage
    # objects). On the demo site we use this on the HomePage
    def children(self, num_pages=3):
        count = EventPage.objects.live().descendant_of(self).filter(start_date__gt=now()).count()
        if count >= num_pages:
            return reversed(EventPage.objects.live().descendant_of(self).filter(start_date__gt=now()).order_by('start_date')[:num_pages])
        else:
            return EventPage.objects.live().descendant_of(self).order_by('-start_date')[:num_pages]

        # return self.get_children().specific().live().order_by('-path')


def blog_page_changed(page):
    # we have EventPage and BlogPage pages
    # with blog index pages
    if page.__class__ == EventPage:
        blog_page = page.blogpage
    elif page.__class__ == BlogPage:
        blog_page = page
    else:
        return

    # Find all the live BlogIndexPages and HomePages that contain this blog_page
    batch = PurgeBatch()

    home_pages = list(HomePage.objects.live())
    for blog_index in BlogIndexPage.objects.live():
        if blog_page in blog_index.get_posts():
            batch.add_page(blog_index)
            for home_page in home_pages.copy():
                if blog_index.page_ptr in [home_page.featured_section_1, home_page.featured_section_2]:
                    batch.add_page(home_page)
                    home_pages.remove(home_page)

    # Purge all the blog indexes and home pages we found in a single request
    batch.purge()


@receiver(page_published)
def page_published_handler(instance, **kwargs):
    blog_page_changed(instance)


@receiver(pre_delete)
def page_deleted_handler(instance, **kwargs):
    blog_page_changed(instance)


@receiver(post_page_move)
def page_post_page_move_handler(instance, **kwargs):
    blog_page_changed(instance.specific)
