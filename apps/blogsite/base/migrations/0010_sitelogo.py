# Generated by Django 4.1.7 on 2023-04-16 17:32

from django.db import migrations, models
import django.db.models.deletion
import wagtail.models


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailimages', '0025_alter_image_file_alter_rendition_file'),
        ('wagtailcore', '0083_workflowcontenttype'),
        ('base', '0009_alter_footertext_unique_together_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteLogo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('live', models.BooleanField(default=True, editable=False, verbose_name='live')),
                ('has_unpublished_changes', models.BooleanField(default=False, editable=False, verbose_name='has unpublished changes')),
                ('first_published_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='first published at')),
                ('last_published_at', models.DateTimeField(editable=False, null=True, verbose_name='last published at')),
                ('go_live_at', models.DateTimeField(blank=True, null=True, verbose_name='go live date/time')),
                ('expire_at', models.DateTimeField(blank=True, null=True, verbose_name='expiry date/time')),
                ('expired', models.BooleanField(default=False, editable=False, verbose_name='expired')),
                ('image_footer', models.ForeignKey(help_text='Format 700 x 200', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='wagtailimages.image')),
                ('image_header', models.ForeignKey(help_text='Format 700 x 200', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='wagtailimages.image')),
                ('latest_revision', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.revision', verbose_name='latest revision')),
                ('live_revision', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.revision', verbose_name='live revision')),
                ('site', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='wagtailcore.site')),
            ],
            options={
                'verbose_name_plural': 'Site Logo',
            },
            bases=(wagtail.models.PreviewableMixin, models.Model),
        ),
    ]