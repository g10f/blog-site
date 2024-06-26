# Generated by Django 5.0.4 on 2024-05-15 20:09

import wagtail.blocks
import wagtail.embeds.blocks
import wagtail.fields
import wagtail.images.blocks
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0010_alter_eventpage_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogindexpage',
            name='body',
            field=wagtail.fields.StreamField([('heading_block', wagtail.blocks.StructBlock([('heading_text', wagtail.blocks.CharBlock(form_classname='title', required=True)), ('size', wagtail.blocks.ChoiceBlock(blank=True, choices=[('', 'Select a header size'), ('h2', 'H2'), ('h3', 'H3'), ('h4', 'H4')], required=False))])), ('paragraph_block', wagtail.blocks.RichTextBlock(icon='pilcrow', template='blocks/paragraph_block.html')), ('image_block', wagtail.blocks.StructBlock([('image', wagtail.images.blocks.ImageChooserBlock(required=True)), ('caption', wagtail.blocks.CharBlock(required=False)), ('attribution', wagtail.blocks.CharBlock(required=False))])), ('video_block', wagtail.blocks.StructBlock([('video_id', wagtail.blocks.CharBlock(required=True)), ('ratio', wagtail.blocks.ChoiceBlock(choices=[('', 'Select a aspect ratio'), ('1x1', '1x1'), ('4x3', '4x3'), ('16x9', '16x9'), ('21x9', '21x9')]))])), ('block_quote', wagtail.blocks.StructBlock([('text', wagtail.blocks.TextBlock()), ('attribute_name', wagtail.blocks.CharBlock(blank=True, label='e.g. Mary Berry', required=False))])), ('embed_block', wagtail.embeds.blocks.EmbedBlock(help_text='Insert an embed URL e.g https://www.youtube.com/embed/SGJFWirQ3ks', icon='media', template='blocks/embed_block.html')), ('RawHTMLBlock', wagtail.blocks.RawHTMLBlock(help_text='Insert raw HTML e.g. <iframe>..</iframe>'))], blank=True, verbose_name='page body'),
        ),
    ]
