import json
import logging
import re
from datetime import timedelta
from functools import partial
from urllib.parse import urlencode, urljoin

import markdown
import wagtail
from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from taggit.models import Tag, TaggedItemBase
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.admin.panels import FieldPanel, InlinePanel, FieldRowPanel
from wagtail.contrib.frontend_cache.utils import PurgeBatch
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import StreamField
from wagtail.models import Page, Orderable, Site, TranslatableMixin
from wagtail.search import index
from wagtail.signals import page_published, page_unpublished, post_page_move

from blogsite.base.blocks import BaseStreamBlock
from blogsite.base.forms import SiteFieldForm
from blogsite.base.models import get_cached_path, purge_index_pages, Speaker
from blogsite.base.views import SiteFieldChooserViewSet

logger = logging.getLogger(__name__)

phone_re = re.compile(r'^(\+\d{1,3})?' + r'((-?\d+)|(\s?\(\d+\)\s?)|\s?\d+){1,9}$')
validate_phone = RegexValidator(phone_re, _("Enter a valid phone number i.e. +49 (531) 123456"), 'invalid')


class BlogPeopleRelationship(Orderable, models.Model):
    page = ParentalKey('BlogPage', related_name='blog_person_relationship', on_delete=models.CASCADE)
    people = models.ForeignKey('base.People', related_name='person_blog_relationship', on_delete=models.CASCADE)
    panels = [FieldPanel('people')]


class EventSpeakerRelationship(Orderable, models.Model):
    page = ParentalKey('EventPage', related_name='event_speaker_relationship', on_delete=models.CASCADE)
    speaker = models.ForeignKey('base.Speaker', related_name='event_speaker_relationship', on_delete=models.CASCADE)
    panels = [FieldPanel('speaker')]


class BlogPageTag(TaggedItemBase):
    """
    This model allows us to create a many-to-many relationship between
    the BlogPage object and tags. There's a longer guide on using it at
    https://docs.wagtail.io/en/latest/reference/pages/model_recipes.html#tagging
    """
    content_object = ParentalKey('BlogPage', related_name='tagged_items', on_delete=models.CASCADE)


class EventTemplateTag(TaggedItemBase):
    """
    This model allows us to create a many-to-many relationship between
    the BlogPage object and tags. There's a longer guide on using it at
    https://docs.wagtail.io/en/latest/reference/pages/model_recipes.html#tagging
    """
    content_object = ParentalKey('EventTemplate', related_name='tagged_items', on_delete=models.CASCADE)


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
            # see https://docs.wagtail.org/en/stable/extending/generic_views.html#limiting-choices-via-linked-fields
            panels=[FieldPanel('people', widget=SiteFieldChooserViewSet(name="people_chooser", model="base.People").widget_class(linked_fields={'site': '#id_site', }))],
            min_num=1),
        FieldPanel('tags'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('subtitle'),
        index.SearchField('introduction'),
        index.SearchField('body'),
        index.SearchField('authors'),
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
        authors = [n.people for n in self.blog_person_relationship.all()]

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
            tag.url = urljoin(self.get_parent().get_url_parts()[2], f'tags/{tag.slug}/')
        return tags

    def get_cached_paths(self):
        # Yield the main URL
        yield '/'

        # make sure all pages are purged
        for tag in self.get_tags:
            yield f'/?tag={tag.slug}'

    # Specifies parent to BlogPage as being BlogIndexPages
    parent_page_types = ['BlogIndexPage']

    # Specifies what content types can exist as children of BlogPage.
    # Empty list means that no child content types are allowed.
    subpage_types = []

    def set_tag(self, request):
        tag = request.GET.get('tag')
        if tag:
            try:
                self.tag = Tag.objects.get(slug=request.GET.get('tag'))
            except Tag.DoesNotExist:
                msg = _('There is no tag "%(tag)s".') % {'tag': tag}
                messages.add_message(request, messages.INFO, msg)
                logger.warning(f'tag {tag} does not exist')

    def serve(self, request, *args, **kwargs):
        self.set_tag(request)
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


# Fields of an EventPage linked to a campai event, which are overwritten by the sync with the data from campai.
# Editors can't change them in the admin.
# is_booked_up is not one of them: the sync only sets it, and only an editor can reset it.
CAMPAI_FIELDS = ['title', 'event_template', 'introduction', 'body', 'start_date', 'end_date', 'location',
                 'max_participants', 'price', 'price_reduced', 'is_cancelled']


class EventPageForm(WagtailAdminPageForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.campai_event_id:
            for field_name in CAMPAI_FIELDS:
                if field_name in self.fields:
                    # a disabled field keeps the value of the page, whatever is submitted
                    self.fields[field_name].disabled = True
                    self.fields[field_name].help_text = _('Maintained in campai.')

    def clean(self):
        cleaned_data = super().clean()
        # The speakers are an inline formset, which can't be disabled like a field.
        formset = self.formsets.get('event_speaker_relationship')
        if self.instance.campai_event_id and formset is not None and formset.is_valid():
            speaker_ids = {form.cleaned_data['speaker'].pk for form in formset.forms
                           if form.cleaned_data.get('speaker') and not form.cleaned_data.get('DELETE')}
            if speaker_ids != {relationship.speaker_id for relationship in self.instance.event_speaker_relationship.all()}:
                raise ValidationError(_('The speakers are maintained in campai.'))
        return cleaned_data


class EventTemplate(TranslatableMixin, index.Indexed, ClusterableModel):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    name = models.CharField("name", max_length=254)
    subtitle = models.CharField(_('subtitle'), blank=True, max_length=255)
    introduction = models.TextField(_('introduction'), help_text='Text to describe the page', blank=True)
    image = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    additional_infos = wagtail.fields.RichTextField(_('additional infos'), blank=True, help_text="Write additional information's", null=True)
    body = StreamField(BaseStreamBlock(), verbose_name=_("page body"), blank=True, use_json_field=True)
    tags = ClusterTaggableManager(through=EventTemplateTag, blank=True)

    base_form_class = SiteFieldForm

    panels = [
        FieldPanel('site'),
        FieldPanel('name'),
        FieldPanel('subtitle'),
        FieldPanel('introduction'),
        FieldPanel('image'),
        FieldPanel('additional_infos'),
        FieldPanel('body'),
        FieldPanel('tags'),
    ]

    def __str__(self):
        return self.name


class EventPage(BlogPage):
    """
    An Event Page

    We access the Speaker object with an inline panel that references the
    ParentalKey's related_name in EventSpeakerRelationship. More docs:
    https://docs.wagtail.io/en/latest/topics/pages.html#inline-models
    """
    intro_template = 'blog/_event_introduction.html'
    parent_page_types = ['EventIndexPage', 'BlogIndexPage']
    event_template = models.ForeignKey('blog.EventTemplate', null=True, blank=True, on_delete=models.SET_NULL)
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
    is_cancelled = models.BooleanField(_('is cancelled'), default=False)
    additional_infos = wagtail.fields.RichTextField(_('additional infos'), blank=True, help_text="Write additional information's", null=True)
    with_registration_form = models.BooleanField("with_registration_form", default=True, help_text=_('Displays a registration form.'))
    highlight_introduction = models.BooleanField(_('highlight introduction'), default=False)
    campai_event_id = models.CharField(_('campai Event ID'), unique=True, blank=True, null=True, default=None)
    # set by the campai sync, see update_campai_statistics
    confirmed_attendees = models.PositiveIntegerField(_('confirmed attendees'), default=0, editable=False)

    base_form_class = EventPageForm

    search_fields = BlogPage.search_fields + [
        index.SearchField('location'),
        index.SearchField('additional_infos'),
        index.SearchField('speakers'),
        # Pull in content from related models too
        index.RelatedFields('event_template', [
            index.SearchField('subtitle'),
            index.SearchField('introduction'),
            index.SearchField('additional_infos'),
            index.SearchField('body'), ]),
    ]

    class Meta:
        verbose_name = _('Event')

    content_panels = Page.content_panels + [
        FieldPanel('event_template'),
        FieldPanel('campai_event_id', read_only=True),
        FieldPanel('subtitle'),
        FieldPanel('introduction'),
        FieldPanel('highlight_introduction'),
        FieldPanel('image'),
        InlinePanel(
            'event_speaker_relationship', label=_("speakers"),
            # see https://docs.wagtail.org/en/stable/extending/generic_views.html#limiting-choices-via-linked-fields
            panels=[FieldPanel('speaker', widget=SiteFieldChooserViewSet(name="speaker_chooser", model="base.Speaker").widget_class(linked_fields={'site': '#id_site', }))],
            min_num=0),
        FieldRowPanel([FieldPanel('start_date'), FieldPanel('end_date'), ]),
        InlinePanel("additional_dates", panels=[FieldRowPanel([FieldPanel('start'), FieldPanel('end'), ]), ], label=_('additional dates')),
        FieldPanel('registration_end_date'),
        FieldPanel('location'),
        FieldPanel('min_participants'),
        FieldPanel('max_participants'),
        FieldPanel('price'),
        FieldPanel('price_reduced'),
        FieldPanel('is_registration_open'),
        FieldPanel('with_registration_form'),
        FieldPanel('registration_email'),
        FieldPanel('registration_phone_number'),
        FieldPanel('is_booked_up'),
        FieldPanel('is_cancelled'),
        FieldPanel('additional_infos'),
        FieldPanel('body'),
        FieldPanel('date_published'),
        InlinePanel(
            'blog_person_relationship', label=_("authors"),
            # see https://docs.wagtail.org/en/stable/extending/generic_views.html#limiting-choices-via-linked-fields
            panels=[FieldPanel('people', widget=SiteFieldChooserViewSet(name="people_chooser", model="base.People").widget_class(linked_fields={'site': '#id_site', }))],
            min_num=0),
        FieldPanel('tags'),
    ]

    @property
    def get_tags(self):
        """
        Similar to the authors function above we're returning all the tags that
        are related to the blog post into a list we can access on the template.
        We're additionally adding a URL to access BlogPage objects with that tag
        """
        tags = self.tags.all()
        if not tags and self.event_template:
            tags = self.event_template.tags.all()

        for tag in tags:
            tag.url = urljoin(self.get_parent().get_url_parts()[2], f'tags/{tag.slug}/')
        return tags

    @property
    def campai_link_text(self):
        if self.max_participants is None:
            return _("Book now")
        else:
            if self.confirmed_attendees < self.max_participants:
                return _("Book now")
            else:
                return _("Add to waiting list")

    def speakers(self):
        speakers = [n.speaker for n in self.event_speaker_relationship.all()]
        return speakers

    def with_content_json(self, content):
        # The number of confirmed attendees is updated without a revision (see update_campai_statistics), so the
        # value of an older revision must not overwrite it, e.g. when an editor publishes a draft.
        obj = super().with_content_json(content)
        obj.confirmed_attendees = self.confirmed_attendees
        return obj

    @property
    def campai_booking_url(self):
        if self.campai_event_id:
            return urljoin(settings.CAMPAI_BASE_URL, f'events/{self.campai_event_id}/checkout')
        else:
            return None

    @property
    def is_registration_expired(self):
        if now() > self.start_date:
            return True
        elif self.campai_event_id:
            # external booking page is responsible
            return False
        elif self.registration_end_date and now() > self.registration_end_date:
            return True
        return False

    @property
    def is_past(self):
        return now() > self.end_date

    @property
    def status_text(self):
        """
        Translated short status of the event for listings and the detail page.
        None for an upcoming event that takes place as planned.
        """
        if self.is_cancelled:
            return _('was cancelled') if self.is_past else _('is cancelled')
        if self.is_past:
            return _('already executed')
        return None

    @property
    def registration_closed_reasons(self):
        """
        Translated texts explaining why registration is no longer possible.
        An empty list means nothing prevents a registration.
        """
        if self.is_cancelled:
            # the other reasons don't matter for a cancelled event
            return [_('The event has been cancelled.')]
        reasons = []
        if self.is_registration_expired:
            reasons.append(_('The registration period has expired.'))
        if self.is_booked_up:
            reasons.append(_('The event is fully booked.'))
        return reasons

    @property
    def is_registration_possible(self):
        # is_registration_open is the editor's switch for events that take registrations at all,
        # so it is not a "closed" reason shown to visitors
        return self.is_registration_open and not self.registration_closed_reasons

    def get_siblings(self, inclusive=True):
        # Overwrite BlogPage.get_siblings that we can order by start_date.
        return EventPage.objects.sibling_of(self, inclusive)

    def get_next_siblings(self, inclusive=False):
        # Order by start_date, date_published
        # take into account more than one event with the same start_date
        q = Q(start_date=self.start_date, date_published__gt=self.date_published) | Q(start_date__gt=self.start_date)
        return self.get_siblings(inclusive).filter(q).order_by("start_date", "date_published")

    def get_prev_siblings(self, inclusive=False):
        # Order by -start_date, -date_published
        # take into account more than one event with the same start_date
        q = Q(start_date=self.start_date, date_published__lt=self.date_published) | Q(start_date__lt=self.start_date)
        return self.get_siblings(inclusive).filter(q).order_by("-start_date", "-date_published")

    def serve(self, request, *args, **kwargs):
        self.set_tag(request)

        from .forms import EventRegistrationForm
        to_email = self.registration_email if self.registration_email else settings.EVENT_REGISTRATION_EMAIL
        landing = request.GET.get('landing', "0")
        if request.method == 'POST':
            subject = _('Registration for "%(event)s"') % {"event": self}
            customer_request = EventRegistration(event=self, subject=subject, to_email=to_email)
            form = EventRegistrationForm(request.POST, instance=customer_request, request=request)
            if form.is_valid():
                form.save()
                # store info that the user filled the form
                params = {'landing': "1"}
                redirect_url = f"{self.url}?{urlencode(params)}"
                return redirect(redirect_url)
            landing = "0"
        else:
            message = _('I would like to register for "%(title)s" at %(data)s.') % {"title": self.title, 'data': self.start_date.date()}
            form = EventRegistrationForm(initial={'message': message}, request=request)

        context = self.get_context(request)
        context["form"] = form
        if landing == "1":
            context["landing"] = landing
            context["message"] = mark_safe(_("Thank you for your registration. If you do not receive a response from us within four days, please send an email to "
                                             "<a href=\"mailto:%(to_email)s\">%(to_email)s</a>.") % {"to_email": to_email})
        return TemplateResponse(request, self.get_template(request), context)

    def __str__(self):
        return f"{timezone.localtime(self.start_date).date()} - {self.title}"

    def clean(self):
        if self.end_date < self.start_date:
            raise forms.ValidationError("The end date must be greater than the start date.")


class EventDate(models.Model):
    start = models.DateTimeField(_('start date'), default=timezone.now)
    end = models.DateTimeField(_('end date'), default=_now_plus_120_minutes)
    page = ParentalKey(EventPage, on_delete=models.CASCADE, related_name='additional_dates', verbose_name=_('additional dates'))

    class Meta:
        verbose_name = _('additional date')
        verbose_name_plural = _('additional dates')


class BlogIndexPage(RoutablePageMixin, Page):
    """
    Index page for blogs.
    We need to alter the page model's context to return the child page objects,
    the BlogPage objects, so that it works as an index page

    RoutablePageMixin is used to allow for a custom sub-URL for the tag views
    defined above.
    """
    introduction = models.TextField(help_text=_('Text to describe the page'), blank=True)
    image = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                              help_text='Landscape mode only; horizontal width between 1000px and 3000px.')
    body = StreamField(BaseStreamBlock(), verbose_name=_("page body"), blank=True, use_json_field=True)

    content_panels = Page.content_panels + [FieldPanel('introduction'), FieldPanel('image'), FieldPanel('body'), ]

    # Specifies that only BlogPage objects can live under this index page
    subpage_types = ['BlogPage']

    # Defines a method to access the children of the page (e.g. BlogPage
    # objects). On the demo site we use this on the HomePage
    def children(self, num_pages=3):
        return self.get_children().specific().live().order_by('-path')[:num_pages]  # return BlogPage.objects.live().descendant_of(self).order_by('-date_published')

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
        year = request.GET.get('year')
        context['year'] = year
        context['posts'] = self.paginate(request, self.get_posts(year=year))
        return context

    # This defines a Custom view that utilizes Tags. This view will return all
    # related BlogPages for a given Tag or redirect back to the BlogIndexPage.
    # More information on RoutablePages is at
    # https://docs.wagtail.io/en/latest/reference/contrib/routablepage.html
    @path('tags/', name='tag_archive')
    @path('tags/<tag>/', name='tag_archive')
    def tag_archive(self, request, tag=None):
        year = request.GET.get('year')
        try:
            tag = Tag.objects.get(slug=tag)
        except Tag.DoesNotExist:
            if tag:
                msg = _('There is no tag "%(tag)s".') % {'tag': tag}
                messages.add_message(request, messages.INFO, msg)
            return redirect(self.url)

        posts = self.paginate(request, self.get_posts(tag=tag, year=year))
        context = super(BlogIndexPage, self).get_context(request)
        context['year'] = year
        context['tag'] = tag
        context['posts'] = posts
        return render(request, self.template, context)

    def get_cached_paths(self):
        # tags of the posts and of the event templates, which events without own tags use
        tags = Tag.objects.filter(Q(blog_blogpagetag_items__isnull=False) | Q(blog_eventtemplatetag_items__isnull=False)).distinct()
        yield from get_cached_path(items=tags, item_attribute='slug',
                                   reverse_subpage=partial(self.reverse_subpage, 'tag_archive'), filter_method=self.get_posts)
        # the pagination links don't keep the year, so only the first page of a year is cached.
        # Including the years of unpublished posts, whose year page may still be in the cache.
        for year in self.get_years(live=False):
            yield f'/?year={year}'

    # Returns the child BlogPage objects for this BlogPageIndex.
    # If a tag is used then it will filter the posts by tag.
    def get_posts(self, tag=None, year=None):
        posts = BlogPage.objects.live().descendant_of(self).order_by('-path')
        if tag:
            posts = posts.filter(tags=tag)
        if year:
            posts = posts.filter(date_published__year=year)
        return posts

    # Returns the list of Tags for all child posts of this BlogPage.
    def get_child_tags(self):
        tags = []
        for post in self.get_posts():
            # Not tags.append() because we don't want a list of lists
            tags += post.get_tags
        tags = sorted(set(tags))
        return tags

    def get_years(self, live=True):
        posts = BlogPage.objects.descendant_of(self)
        if live:
            posts = posts.live()
        years = []
        for post in posts.order_by('-date_published').dates('date_published', 'year'):
            years.append(post.year)
        return years


class EventIndexPage(BlogIndexPage):
    subpage_types = ['EventPage']

    # Returns the child BlogPage objects for this BlogPageIndex.
    # If a tag is used then it will filter the posts by tag.
    def get_posts(self, tag=None, year=None):
        posts = EventPage.objects.live().descendant_of(self).order_by('-start_date', '-date_published')

        if tag:
            # an event without own tags uses the tags of its event template
            posts = posts.filter(Q(tags=tag) | (Q(tags=None) & Q(event_template__tags=tag)))
        if year:
            posts = posts.filter(start_date__year=year)
        return posts

    def get_years(self, live=True):
        posts = EventPage.objects.descendant_of(self)
        if live:
            posts = posts.live()
        years = []
        for post in posts.order_by('-start_date', '-date_published').dates('start_date', 'year'):
            years.append(post.year)
        return years

    # Defines a method to access the children of the page (e.g. BlogPage
    # objects). On the demo site we use this on the HomePage
    def children(self, num_pages=3):
        count = EventPage.objects.live().descendant_of(self).filter(end_date__gt=now()).count()
        if count >= num_pages:
            return reversed(EventPage.objects.live().descendant_of(self).filter(end_date__gt=now()).order_by('end_date')[:num_pages])
        else:
            return EventPage.objects.live().descendant_of(self).order_by('-end_date')[:num_pages]


class EventRegistration(models.Model):
    event = models.ForeignKey(EventPage, related_name='event', blank=True, null=True, on_delete=models.SET_NULL)
    submit_time = models.DateTimeField(auto_now=True, verbose_name='submit_time')
    subject = models.CharField(_('subject'), max_length=255)
    name = models.CharField(verbose_name=_("first name and last name"), max_length=255)
    email = models.EmailField()
    telephone = models.CharField(_('telephone'), max_length=20, blank=True)
    message = models.TextField(_("message"))
    to_email = models.EmailField()
    is_member = models.BooleanField(_("member"), default=False)
    send_email_copy_to_myself = models.BooleanField(_("send a copy of the registration to myself"), default=True)

    class Meta:
        verbose_name = _('Registration')
        verbose_name_plural = _('Registrations')
        ordering = ['-submit_time']

    panels = [FieldPanel('event'), FieldPanel('submit_time', read_only=True), FieldPanel('subject'), FieldPanel('name'), FieldPanel('email'), FieldPanel('telephone'),
              FieldPanel('message'), FieldPanel('is_member'), ]

    def __str__(self):
        return f"{self.event} {self.name}"


def get_campai_event_index():
    # New campai events are added to the EventIndexPage configured with CAMPAI_EVENT_INDEX_PAGE_ID,
    # without configuration to the first one, which is only unambiguous with a single EventIndexPage.
    if settings.CAMPAI_EVENT_INDEX_PAGE_ID:
        return EventIndexPage.objects.get(pk=settings.CAMPAI_EVENT_INDEX_PAGE_ID)

    event_indexes = EventIndexPage.objects.order_by('pk')
    if event_indexes.count() > 1:
        logger.warning("There are several EventIndexPages, new campai events are added to the first one. "
                       "Set CAMPAI_EVENT_INDEX_PAGE_ID to choose one.")
    event_index = event_indexes.first()
    if event_index is None:
        raise ImproperlyConfigured("There is no EventIndexPage for the campai events.")
    return event_index


def update_campai_statistics(event_page, event_data):
    # The number of confirmed attendees changes with every booking. It is saved without a new revision, so that the
    # revision history isn't flooded and drafts of editors are not affected (see EventPage.with_content_json).
    confirmed_attendees = (event_data.get("statistics") or {}).get("confirmed", 0)
    if confirmed_attendees == event_page.confirmed_attendees:
        return False
    event_page.confirmed_attendees = confirmed_attendees
    if event_page.id is not None:
        EventPage.objects.filter(pk=event_page.pk).update(confirmed_attendees=confirmed_attendees)
    return True


def update_or_create_event_from_campai(event_data):
    # event_data is an event of the campai event list
    event_index = None  # only set for a new event_page, which is added to this EventIndexPage at the end
    campai_event_id = event_data["_id"]
    try:
        event_page = EventPage.objects.get(campai_event_id=campai_event_id)
    except EventPage.DoesNotExist:
        event_page = EventPage(campai_event_id=campai_event_id)
        event_index = get_campai_event_index()

    # event templates and speakers are looked up in the site and locale of the event
    if event_index is None:
        site = event_page.get_site()
        locale = event_page.locale
    else:
        site = event_index.get_site()
        locale = event_index.locale

    changed_fields = []

    def update_field(field_name, new_value):
        old_value = getattr(event_page, field_name)
        if old_value != new_value:
            setattr(event_page, field_name, new_value)
            changed_fields.append(field_name)

    def get_event_template():
        return EventTemplate.objects.filter(site=site, locale=locale, name=event_data["info"]["title"]).first()

    def price(name):
        if event_data["offer"]["rates"]:
            rate = next(filter(lambda x: x["name"] == name, event_data["offer"]["rates"]), None)
            if rate is not None and "charge" in rate and "price" in rate["charge"] and rate["charge"]["price"] is not None:
                return rate["charge"]["price"]["price"] / 100
        return None

    def event_speakers():
        if "categories" in event_data["info"]:
            speaker_tag = "Dozent:"
            dozenten = filter(lambda x: x["name"].startswith(speaker_tag), event_data["info"]["categories"])
            allow_unicode = getattr(settings, "WAGTAIL_ALLOW_UNICODE_SLUGS", True)
            speakers = Speaker.objects.filter(site=site, slug__in=[slugify(x["name"][len(speaker_tag):], allow_unicode=allow_unicode) for x in dozenten])
            return [EventSpeakerRelationship(speaker_id=speaker.id) for speaker in speakers]
        return []

    def event_location():
        if event_data and "categories" in event_data["info"]:
            location_tag = "Ort:"
            location_category = next(filter(lambda x: x["name"].startswith(location_tag), event_data["info"]["categories"]), None)
            if location_category is not None:
                return location_category["name"][len(location_tag):]
        return ""

    def get_body():
        if event_data and "details" in event_data["info"]:
            details_html = markdown.markdown(event_data["info"]["details"])
            body = json.dumps([{"type": "RawHTMLBlock", "value": details_html}])
            return body
        else:
            return StreamField(BaseStreamBlock()).stream_block.to_python(None)

    # before the content, so that a published revision keeps the new statistics
    statistics_changed = update_campai_statistics(event_page, event_data)

    # only set, an editor resets it in the admin
    if (event_data.get("statistics") or {}).get("waitlisted", 0) >= settings.CAMPAI_MAX_WAITLISTED:
        update_field("is_booked_up", True)

    if event_data["cancelation"] is not None:
        update_field("is_cancelled", True)
    else:
        update_field("is_cancelled", False)

    update_field("title", event_data["info"]["title"])
    update_field("event_template", get_event_template())
    if not event_page.event_template:
        update_field("introduction", event_data["info"]["description"])
        update_field("body", get_body())
    else:
        update_field("introduction", "")
        update_field("body", StreamField(BaseStreamBlock()).stream_block.to_python(None))

    update_field("start_date", parse_datetime(event_data["period"]["from"]))
    update_field("end_date", parse_datetime(event_data["period"]["to"]))
    update_field("max_participants", event_data["settings"]["maxAttendees"])
    update_field("price", price("Standard"))
    update_field("price_reduced", price("Mitglieder"))

    # only update speakers if really changed. Otherwise, saved draft of the page gets invalid because of unknown reason.
    new_event_speakers = event_speakers()
    if {x.speaker_id for x in new_event_speakers} != {x.speaker_id for x in event_page.event_speaker_relationship.all()}:
        update_field("event_speaker_relationship", new_event_speakers)
    update_field("location", event_location())

    if event_index is None:
        if len(changed_fields) > 0:
            # The campai changes are published on the live page. A draft of an editor would be replaced by this
            # revision, so the campai changes are saved on top of the draft as a new draft revision.
            draft = event_page.get_latest_revision_as_object() if event_page.has_unpublished_changes else None
            event_page.latest_revision_created_at = now()
            event_page.save_revision().publish()
            if draft is not None:
                for field_name in changed_fields:
                    if field_name == "event_speaker_relationship":
                        # new relationship objects, because the ones above belong to the live page
                        draft.event_speaker_relationship = event_speakers()
                    else:
                        setattr(draft, field_name, getattr(event_page, field_name))
                draft.save_revision()
        elif statistics_changed:
            # the statistics are shown on the event page only, a published revision purges it anyway
            batch = PurgeBatch()
            batch.add_page(event_page)
            batch.purge()
    else:
        event_page.locale = locale
        event_index.add_child(instance=event_page)


def blog_page_changed(blog_page, parent_page_before=None):
    # Purge all the live BlogIndexPages and EventIndexPages containing this blog_page (BlogPage or EventPage),
    # ignoring whether the blog_page itself is live, so that an unpublished blog_page disappears from the indexes as
    # well. After a move, the index the blog_page was moved away from is purged too.
    # specific(), so that an EventIndexPage enumerates its cached paths with its own get_posts and get_years.
    blog_indexes = list(BlogIndexPage.objects.live().ancestor_of(blog_page).specific())
    if parent_page_before is not None:
        blog_indexes += BlogIndexPage.objects.live().ancestor_of(parent_page_before, inclusive=True).specific()
    purge_index_pages(blog_indexes)


# page_published, page_unpublished and post_page_move are sent with the specific class as sender
@receiver([page_published, page_unpublished], sender=BlogPage)
@receiver([page_published, page_unpublished], sender=EventPage)
def blog_page_published_handler(instance, **kwargs):
    blog_page_changed(instance)


@receiver(post_page_move, sender=BlogPage)
@receiver(post_page_move, sender=EventPage)
def blog_page_moved_handler(instance, parent_page_before, **kwargs):
    blog_page_changed(instance.specific, parent_page_before)


# deleting an EventPage deletes its BlogPage parent row as well, so BlogPage covers both
@receiver(pre_delete, sender=BlogPage)
def blog_page_deleted_handler(instance, **kwargs):
    blog_page_changed(instance)
