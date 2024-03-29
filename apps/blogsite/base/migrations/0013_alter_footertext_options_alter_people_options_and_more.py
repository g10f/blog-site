# Generated by Django 4.2.4 on 2023-08-09 10:41

from django.db import migrations, models
import wagtail.fields


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0012_people_description_alter_homepage_hero_cta_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='footertext',
            options={'verbose_name': 'Fußzeile', 'verbose_name_plural': 'Fußzeilen'},
        ),
        migrations.AlterModelOptions(
            name='people',
            options={'verbose_name': 'Person', 'verbose_name_plural': 'Personen'},
        ),
        migrations.AlterModelOptions(
            name='speaker',
            options={'verbose_name': 'Referent', 'verbose_name_plural': 'Referenten'},
        ),
        migrations.AlterField(
            model_name='people',
            name='description',
            field=wagtail.fields.RichTextField(blank=True, verbose_name='description'),
        ),
        migrations.AlterField(
            model_name='people',
            name='first_name',
            field=models.CharField(max_length=254, verbose_name='first name'),
        ),
        migrations.AlterField(
            model_name='people',
            name='job_title',
            field=models.CharField(blank=True, max_length=254, verbose_name='job title'),
        ),
        migrations.AlterField(
            model_name='people',
            name='last_name',
            field=models.CharField(max_length=254, verbose_name='last name'),
        ),
        migrations.AlterField(
            model_name='speaker',
            name='description',
            field=wagtail.fields.RichTextField(blank=True, verbose_name='description'),
        ),
        migrations.AlterField(
            model_name='speaker',
            name='first_name',
            field=models.CharField(max_length=254, verbose_name='first name'),
        ),
        migrations.AlterField(
            model_name='speaker',
            name='job_title',
            field=models.CharField(blank=True, max_length=254, verbose_name='job title'),
        ),
        migrations.AlterField(
            model_name='speaker',
            name='last_name',
            field=models.CharField(max_length=254, verbose_name='last name'),
        ),
    ]
