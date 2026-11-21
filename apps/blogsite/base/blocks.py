from wagtail.blocks import (
    CharBlock, ChoiceBlock, RichTextBlock, StreamBlock, StructBlock, TextBlock,
)
from wagtail.images.blocks import ImageChooserBlock


class YouTubeVideoBlock(StructBlock):
    video_id = CharBlock(required=True)
    ratio = ChoiceBlock(choices=[
        ('', 'Select a aspect ratio'),
        ('1x1', '1x1'),
        ('4x3', '4x3'),
        ('16x9', '16x9'),
        ('21x9', '21x9')
    ], default='16x9', required=True)
    class Meta:
        icon = 'media'
        template = "blocks/video_block.html"


class ImageBlock(StructBlock):
    """
    Custom `StructBlock` for utilizing images with associated caption and
    attribution data
    """
    image = ImageChooserBlock(required=True)
    caption = CharBlock(required=False)
    attribution = CharBlock(required=False)

    class Meta:
        icon = 'image'
        template = "blocks/image_block.html"


class HeadingBlock(StructBlock):
    """
    Custom `StructBlock` that allows the user to select h2 - h4 sizes for headers
    """
    heading_text = CharBlock(classname="title", required=True)
    size = ChoiceBlock(choices=[
        ('', 'Select a header size'),
        ('h2', 'H2'),
        ('h3', 'H3'),
        ('h4', 'H4')
    ], blank=True, required=False)

    class Meta:
        icon = "title"
        template = "blocks/heading_block.html"


class BlockQuote(StructBlock):
    """
    Custom `StructBlock` that allows the user to attribute a quote to the author
    """
    text = TextBlock()
    attribute_name = CharBlock(
        blank=True, required=False, label='e.g. Mary Berry')

    class Meta:
        icon = "openquote"
        template = "blocks/blockquote.html"


class PersonBlock(StructBlock):
    first_name = CharBlock()
    surname = CharBlock()
    photo = ImageChooserBlock(required=False)
    biography = RichTextBlock(features=['h2', 'h3', 'h4', 'bold', 'italic', 'link', 'ol', 'ul', 'document-link'])

    class Meta:
        icon = 'user'
        template = 'blocks/person.html'


# StreamBlocks
class BaseStreamBlock(StreamBlock):
    """
    Define the custom blocks that `StreamField` will utilize
    """
    heading_block = HeadingBlock()
    paragraph_block = RichTextBlock(
        icon="pilcrow",
        template="blocks/paragraph_block.html"
    )
    image_block = ImageBlock()
    video_block = YouTubeVideoBlock()
    block_quote = BlockQuote()
    # no embed_block: an oEmbed embeds YouTube without the privacy mode and any other provider, which the privacy
    # policy of the sites would have to name; videos go into the video_block (youtube-nocookie.com). The rich text
    # has no "embed" either (WAGTAILADMIN_RICH_TEXT_EDITORS in settings/base.py).
    # no raw HTML block: it lets editors put scripts and content of other providers into a page, which reach the
    # admin sessions of the other organisations of an instance and are not named in the privacy policy
