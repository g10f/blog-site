# Generated by Django 5.1.3 on 2024-11-24 21:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0012_eventpage_highlight_introduction'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='eventregistration',
            options={'ordering': ['-submit_time'], 'verbose_name': 'Registration', 'verbose_name_plural': 'Registrations'},
        ),
    ]