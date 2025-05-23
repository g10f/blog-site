# Generated by Django 5.2 on 2025-04-27 19:36

import blogsite.blog.models
import django.db.models.deletion
import django.utils.timezone
import modelcluster.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0013_alter_eventregistration_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventregistration',
            name='send_email_copy_to_myself',
            field=models.BooleanField(default=True, verbose_name='send a copy of the registration to myself'),
        ),
        migrations.CreateModel(
            name='EventDate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateTimeField(default=django.utils.timezone.now, verbose_name='start date')),
                ('end', models.DateTimeField(default=blogsite.blog.models._now_plus_120_minutes, verbose_name='end date')),
                ('page', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='additional_dates', to='blog.eventpage', verbose_name='additional dates')),
            ],
            options={
                'verbose_name': 'additional date',
                'verbose_name_plural': 'additional dates',
            },
        ),
    ]
