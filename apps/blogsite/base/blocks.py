from wagtail.blocks import (
    CharBlock, ChoiceBlock, RichTextBlock, StreamBlock, StructBlock, TextBlock,
)
from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.blocks.field_block import RawHTMLBlock


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
    embed_block = EmbedBlock(
        help_text='Insert an embed URL e.g https://www.youtube.com/embed/SGJFWirQ3ks',
        icon="media",
        template="blocks/embed_block.html")
    RawHTMLBlock = RawHTMLBlock(
        help_text='Insert raw HTML e.g. <iframe>..</iframe>',
        )
