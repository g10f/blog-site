# SocialMediaSettings becomes SiteSettings (shown as "website" in the admin), its field twitter becomes x, and the
# menu title of the home page moves from HomePage.menu_title (0021) into these settings, so that it works whatever
# page type the home page of a site has. The order keeps the values: add the new field, copy, then remove the old one.

from django.db import migrations, models

OLD_MODEL = 'socialmediasettings'
NEW_MODEL = 'sitesettings'


def copy_to_site_settings(apps, schema_editor):
    """Copy a non-empty HomePage.menu_title of a site's root page into that site's settings."""
    Site = apps.get_model('wagtailcore', 'Site')
    HomePage = apps.get_model('base', 'HomePage')
    SiteSettings = apps.get_model('base', 'SiteSettings')
    for site in Site.objects.all():
        home_page = HomePage.objects.filter(page_ptr_id=site.root_page_id).exclude(menu_title='').first()
        if home_page is None:
            continue
        site_settings, _ = SiteSettings.objects.get_or_create(site=site)
        site_settings.home_menu_title = home_page.menu_title
        site_settings.save()


def copy_back_to_home_page(apps, schema_editor):
    """Reverse: put the menu title back on the root page of each site, if that page is a HomePage."""
    HomePage = apps.get_model('base', 'HomePage')
    SiteSettings = apps.get_model('base', 'SiteSettings')
    for site_settings in SiteSettings.objects.exclude(home_menu_title=''):
        HomePage.objects.filter(page_ptr_id=site_settings.site.root_page_id).update(
            menu_title=site_settings.home_menu_title)


def rename_permissions(old_model, new_model, new_verbose_name):
    """Django does not rename the permissions of a renamed model. Without this, groups that may edit the settings
    would keep only the old permissions, which nothing checks any more, and lose access."""
    def rename(apps, schema_editor):
        Permission = apps.get_model('auth', 'Permission')
        for action in ('add', 'change', 'delete', 'view'):
            Permission.objects.filter(content_type__app_label='base', codename=f'{action}_{old_model}').update(
                codename=f'{action}_{new_model}', name=f'Can {action} {new_verbose_name}')
    return rename


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('base', '0021_homepage_menu_title'),
    ]

    operations = [
        migrations.RenameModel(old_name='SocialMediaSettings', new_name='SiteSettings'),
        migrations.RenameField(model_name=NEW_MODEL, old_name='twitter', new_name='x'),
        migrations.AlterField(
            model_name=NEW_MODEL,
            name='x',
            field=models.URLField(blank=True, help_text='Your X profile URL, e.g. https://x.com/name', verbose_name='X'),
        ),
        migrations.AddField(
            model_name=NEW_MODEL,
            name='home_menu_title',
            field=models.CharField(blank=True, help_text='Text of the menu entry of the home page. If empty, "Homepage" is shown.', max_length=255, verbose_name='menu title of the home page'),
        ),
        migrations.RunPython(copy_to_site_settings, copy_back_to_home_page),
        migrations.RemoveField(model_name='homepage', name='menu_title'),
        migrations.AlterModelOptions(
            name=NEW_MODEL,
            options={'verbose_name': 'website', 'verbose_name_plural': 'website'},
        ),
        migrations.RunPython(
            rename_permissions(OLD_MODEL, NEW_MODEL, 'website'),
            rename_permissions(NEW_MODEL, OLD_MODEL, 'social media settings')),
    ]
