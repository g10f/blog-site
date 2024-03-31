from django import forms
from wagtail.admin.mail import send_mail

from .models import EventRegistration


class EventRegistrationForm(forms.ModelForm):
    class Meta:
        model = EventRegistration
        fields = ['name', 'telephone', 'email', 'message']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telephone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'mail@example.com'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Message', "style": "height: 100px"}),
        }

    def render_email(self, instance):
        content = []
        content.append("{}: {}".format('title', instance.event.title))
        content.append("{}: {}".format('date', instance.event.start_date.date()))
        content.append("{}: {}".format('name', instance.name))
        content.append("{}: {}".format('telephone', instance.telephone))
        content.append("{}: {}".format('email', instance.email))
        content.append("{}: {}".format('message', instance.message))
        return "\n".join(content)

    def send_mail(self, instance):
        send_mail(instance.subject, self.render_email(instance), [instance.to_email], reply_to=(instance.email,))

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if instance.to_email:
            self.send_mail(instance)
