# Generated by Django 5.2.1 on 2025-05-31 10:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0014_alter_eventregistration_send_email_copy_to_myself_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventpage',
            name='is_cancelled',
            field=models.BooleanField(default=False, verbose_name='is cancelled'),
        ),
    ]
