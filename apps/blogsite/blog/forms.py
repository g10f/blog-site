from django import forms
from django.utils.translation import gettext as _
from django_recaptcha.fields import ReCaptchaField
from wagtail.admin.mail import send_mail
from wagtail.models.sites import Site

from .models import EventRegistration


class EventRegistrationForm(forms.ModelForm):
    captcha = ReCaptchaField(label=_("Captcha"))

    class Meta:
        model = EventRegistration
        fields = ['name', 'telephone', 'email', 'message', 'is_member', 'send_email_copy_to_myself', 'captcha']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name and last name'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telephone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'mail@example.com'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Message', "style": "height: 100px"}),
            'is_member': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_email_copy_to_myself': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if request is not None:
            self.fields['is_member'].label = _('Member of {site_name}').format(site_name=Site.find_for_request(request).site_name)

    def render_email(self, instance):
        content = []
        content.append(_("Title: {title}").format(title=instance.event.title))
        start_date = instance.event.start_date.date()
        content.append(_("Date: {date}").format(date=start_date))
        for additional_date in instance.event.additional_dates.all():
            # only add if date is different
            if start_date != additional_date.start.date():
                start_date = additional_date.start.date()
                content.append(_("Date: {date}").format(date=start_date))
        content.append(_("Location: {location}").format(location=instance.event.location))
        content.append(_("Name: {name}").format(name=instance.name))
        content.append(_("Telephone: {telephone}").format(telephone=instance.telephone))
        content.append(_("Email: {email}").format(email=instance.email))
        if instance.is_member:
            content.append(_("Is member: True"))
        else:
            content.append(_("Is member: False"))
        content.append(_("Message: {message}").format(message=instance.message))
        return "\n".join(content)

    def send_mail(self, instance):
        cc = []
        if instance.send_email_copy_to_myself:
            cc.append(instance.email)

        send_mail(instance.subject, self.render_email(instance), [instance.to_email], reply_to=(instance.email,), cc=cc)

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if instance.to_email:
            self.send_mail(instance)
