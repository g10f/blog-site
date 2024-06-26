# Generated by Django 5.0.3 on 2024-04-02 17:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0009_eventpage_with_registration_form_eventregistration'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='eventpage',
            options={'verbose_name': 'Event'},
        ),
        migrations.AlterModelOptions(
            name='eventregistration',
            options={'verbose_name': 'Registration', 'verbose_name_plural': 'Registrations'},
        ),
        migrations.AddField(
            model_name='eventregistration',
            name='is_member',
            field=models.BooleanField(default=False, verbose_name='member'),
        ),
        migrations.AddField(
            model_name='eventregistration',
            name='send_email_copy_to_myself',
            field=models.BooleanField(default=False, verbose_name='send a copy of the registration to myself'),
        ),
        migrations.AlterField(
            model_name='eventregistration',
            name='name',
            field=models.CharField(max_length=255, verbose_name='first name and last name'),
        ),
    ]
