import logging

from captcha.fields import ReCaptchaField
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.edit_handlers import FieldPanel, MultiFieldPanel, PageChooserPanel, FieldRowPanel, \
    InlinePanel
from wagtail.contrib.forms.forms import FormBuilder
from wagtail.contrib.forms.models import AbstractEmailForm, AbstractFormField
from wagtail.contrib.settings.models import BaseSetting, BaseSiteSetting
from wagtail.contrib.settings.registry import register_setting
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core.models import Page, TranslatableMixin, _copy
from wagtail.models import Site
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from .blocks import BaseStreamBlock, PersonBlock
from .. import settings

logger = logging.getLogger(__name__)


@register_snippet
class People(TranslatableMixin, index.Indexed, ClusterableModel):
    """
    A Django model to store People objects.
    It uses the `@register_snippet` decorator to allow it to be accessible
    via the Snippets UI (e.g. /admin/snippets/base/people/)

    `People` uses the `ClusterableModel`, which allows the relationship with
    another model to be stored locally to the 'parent' model (e.g. a PageModel)
    until the parent is explicitly saved. This allows the editor to use the
    'Preview' button, to preview the content, without saving the relationships
    to the database.
    https://github.com/wagtail/django-modelcluster
    """
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), null=True, blank=True, on_delete=models.SET_NULL)

    first_name = models.CharField("First name", max_length=254)
    last_name = models.CharField("Last name", max_length=254)
    job_title = models.CharField("Job title", max_length=254)
    slug = models.SlugField(allow_unicode=True, blank=True, unique=True)

    image = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    panels = [FieldPanel('user'), FieldPanel('site'),
              MultiFieldPanel([FieldRowPanel([FieldPanel('first_name', classname="col6"), FieldPanel('last_name', classname="col6"), ])], "Name"),
              FieldPanel('job_title'), FieldPanel('image')]

    search_fields = [index.SearchField('first_name'), index.SearchField('last_name'), index.FilterField('locale_id')]

    @property
    def thumb_image(self):
        # Returns an empty string if there is no profile pic or the rendition
        # file can't be found.
        try:
            return self.image.get_rendition('fill-50x50').img_tag()
        except Exception as e:  # noqa:B901,E722
            logger.exception(e)
            return ''

    def __str__(self):
        return '{} {}'.format(self.first_name, self.last_name)

    class Meta:
        verbose_name = 'Person'
        verbose_name_plural = 'People'
        unique_together = [("translation_key", "locale")]

    def copy_for_translation(self, locale):
        """
        exclude index_entries, because coping fails.
        """
        translated, child_object_map = _copy(self, exclude_fields='index_entries')
        translated.locale = locale

        # Update locale on any translatable child objects as well
        # Note: If this is not a subclass of ClusterableModel, child_object_map will always be '{}'
        for (child_relation, old_pk), child_object in child_object_map.items():
            if isinstance(child_object, TranslatableMixin):
                child_object.locale = locale

        return translated

    def full_clean(self, exclude=None, validate_unique=True):
        if not self.slug:
            # Try to auto-populate slug from title
            allow_unicode = getattr(settings, "WAGTAIL_ALLOW_UNICODE_SLUGS", True)
            self.slug = slugify(f'{self.first_name}-{self.last_name}', allow_unicode=allow_unicode)

        return super().full_clean(exclude, validate_unique)


@register_snippet
class FooterText(TranslatableMixin, models.Model):
    """
    This provides editable text for the site footer. Again it uses the decorator
    `register_snippet` to allow it to be accessible via the admin. It is made
    accessible on the template via a template tag defined in base/templatetags/
    navigation_tags.py
    """
    body = models.TextField(blank=True)
    # body = RichTextField()

    panels = [FieldPanel('body'), ]

    def __str__(self):
        return "Footer text"

    class Meta:
        verbose_name_plural = 'Footer Text'
        unique_together = [("translation_key", "locale")]


class StandardPage(Page):
    """
    A generic content page. It could be used for any type of page content that only needs a title,
    image, introduction and body field
    """

    introduction = models.TextField(help_text='Text to describe the page', blank=True)
    image = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                              help_text='Landscape mode only; horizontal width between 1000px and 3000px.')
    body = StreamField(BaseStreamBlock(), verbose_name="Page body", blank=True, use_json_field=True)
    content_panels = Page.content_panels + [
        FieldPanel('introduction'),
        FieldPanel('body'),
        FieldPanel('image'), ]

    search_fields = Page.search_fields + [
        index.SearchField('introduction'),
        index.SearchField('body'),
    ]


class PersonsPage(Page):
    """
    A generic content page. It could be used for any type of page content that only needs a title,
    image, introduction and body field
    """

    introduction = models.TextField(help_text='Text to describe the page', blank=True)
    image = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                              help_text='Landscape mode only; horizontal width between 1000px and 3000px.')
    body = StreamField([('person', PersonBlock())], verbose_name="Page body", blank=True, use_json_field=True)
    content_panels = Page.content_panels + [FieldPanel('introduction'), FieldPanel('image'), FieldPanel('body'), ]

    search_fields = Page.search_fields + [
        index.SearchField('introduction'),
        index.SearchField('body'),
    ]


class HomePage(Page):
    """
    The Home Page. This looks slightly more complicated than it is. You can
    see if you visit your site and edit the homepage that it is split between
    a:
    - Hero area
    - Body area
    - A promotional area
    - Moveable featured site sections
    """

    # Hero section of HomePage
    image = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', help_text='Homepage image')
    hero_text = models.CharField(max_length=255, help_text='Write an introduction for the site')
    hero_cta = models.CharField(verbose_name='Hero CTA', max_length=255, help_text='Text to display on Call to Action')
    hero_cta_link = models.ForeignKey('wagtailcore.Page', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Hero CTA link',
                                      help_text='Choose a page to link to for the Call to Action')

    # Body section of the HomePage
    body = StreamField(BaseStreamBlock(), verbose_name="Home content block", blank=True, use_json_field=True)

    # Promo section of the HomePage
    promo_image = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', help_text='Promo image')
    promo_title = models.CharField(null=True, blank=True, max_length=255, help_text='Title to display above the promo copy')
    promo_text = RichTextField(null=True, blank=True, help_text='Write some promotional copy')

    # Featured sections on the HomePage
    # You will see on templates/base/home_page.html that these are treated
    # in different ways, and displayed in different areas of the page.
    # Each list their children items that we access via the children function
    # that we define on the individual Page models e.g. BlogIndexPage
    featured_section_1_title = models.CharField(null=True, blank=True, max_length=255, help_text='Title to display above the promo copy')
    featured_section_1 = models.ForeignKey('wagtailcore.Page', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                           help_text='First featured section for the homepage. Will display up to three child items.',
                                           verbose_name='Featured section 1')

    featured_section_2_title = models.CharField(null=True, blank=True, max_length=255, help_text='Title to display above the promo copy')
    featured_section_2 = models.ForeignKey('wagtailcore.Page', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                           help_text='Second featured section for the homepage. Will display up to three child items.',
                                           verbose_name='Featured section 2')

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel('image'),
                FieldPanel('hero_text'),
                MultiFieldPanel(
                    [
                        FieldPanel('hero_cta'),
                        PageChooserPanel('hero_cta_link'),
                    ]),
            ], heading="Hero section"),
        MultiFieldPanel(
            [
                FieldPanel('promo_image'),
                FieldPanel('promo_title'),
                FieldPanel('promo_text'),
            ], heading="Promo section"),
        FieldPanel('body'),
        MultiFieldPanel(
            [
                MultiFieldPanel(
                    [
                        FieldPanel('featured_section_1_title'),
                        PageChooserPanel('featured_section_1'),
                    ]),
                MultiFieldPanel(
                    [
                        FieldPanel('featured_section_2_title'),
                        PageChooserPanel('featured_section_2'),
                    ]),
            ], heading="Featured homepage sections", classname="collapsible")]

    search_fields = Page.search_fields + [
        index.SearchField('body'),
    ]

    def __str__(self):
        return self.title


class FormField(AbstractFormField):
    """
    Wagtailforms is a module to introduce simple forms on a Wagtail site. It
    isn't intended as a replacement to Django's form support but as a quick way
    to generate a general purpose data-collection form or contact form
    without having to write code. We use it on the site for a contact form. You
    can read more about Wagtail forms at:
    https://docs.wagtail.io/en/latest/reference/contrib/forms/index.html
    """
    page = ParentalKey('FormPage', related_name='form_fields', on_delete=models.CASCADE)


class CustomFormBuilder(FormBuilder):
    CAPTCHA_FIELD_NAME = 'wagtailcaptcha'

    def get_create_field_function(self, type):
        """
        Override the method to prepare a wrapped function that will call the original
        function (which returns a field) and update the widget's attrs with a custom
        value that can be used within the template when rendering each field.
        """

        create_field_function = super().get_create_field_function(type)

        def wrapped_create_field_function(field, options):
            created_field = create_field_function(field, options)
            created_field.widget.attrs.update({"class": 'form-control'})
            return created_field

        return wrapped_create_field_function

    @property
    def formfields(self):
        # Add ReCaptcha to formfields property
        fields = super().formfields
        fields[self.CAPTCHA_FIELD_NAME] = ReCaptchaField(label=_("Captcha"))

        return fields


def remove_captcha_field(form):
    form.fields.pop(CustomFormBuilder.CAPTCHA_FIELD_NAME, None)
    form.cleaned_data.pop(CustomFormBuilder.CAPTCHA_FIELD_NAME, None)


class FormPage(AbstractEmailForm):
    form_builder = CustomFormBuilder
    image = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    body = StreamField(BaseStreamBlock(), use_json_field=True)
    thank_you_text = RichTextField(blank=True)

    def process_form_submission(self, form):
        remove_captcha_field(form)
        return super().process_form_submission(form)

    # Note how we include the FormField object via an InlinePanel using the
    # related_name value
    content_panels = AbstractEmailForm.content_panels + [FieldPanel('image'), FieldPanel('body'), InlinePanel('form_fields', label="Form fields"),
                                                         FieldPanel('thank_you_text'), MultiFieldPanel(
            [FieldRowPanel([FieldPanel('from_address', classname="col6"), FieldPanel('to_address', classname="col6"), ]), FieldPanel('subject'), ], "Email"), ]


@register_setting
class SocialMediaSettings(BaseSiteSetting):
    facebook = models.URLField(blank=True, help_text='Your Facebook page URL')
    instagram = models.URLField(blank=True, help_text='Your Instagram URL')
    youtube = models.URLField(blank=True, help_text='Your YouTube channel or user account URL')
    twitter = models.URLField(blank=True, help_text='Your Twitter page URL')

    @property
    def social_media(self):
        return [
            {'id': 'facebook', 'url': self.facebook},
            {'id': 'instagram', 'url': self.instagram},
            {'id': 'youtube', 'url': self.youtube},
            {'id': 'twitter', 'url': self.twitter},
        ]
