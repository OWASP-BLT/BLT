from captcha.fields import CaptchaField
from django import forms
from mdeditor.fields import MDTextFormField

from .models import Monitor, UserProfile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("user_avatar",)


class UserDeleteForm(forms.Form):
    delete = forms.BooleanField(required=True)


class HuntForm(forms.Form):
    content = MDTextFormField()
    start_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"class": "col-sm-6", "readonly": True}),
        label="",
        required=False,
    )
    end_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"class": "col-sm-6", "readonly": True}),
        label="",
        required=False,
    )


class CaptchaForm(forms.Form):
    captcha = CaptchaField()


class QuickIssueForm(forms.Form):
    url = forms.CharField()
    label = forms.CharField()
    description = forms.CharField()


from datetime import datetime


class MonitorForm(forms.ModelForm):
    created = forms.DateTimeField(widget=forms.HiddenInput(), required=False, label="Created")
    modified = forms.DateTimeField(widget=forms.HiddenInput(), required=False, label="Modified")

    class Meta:
        model = Monitor
        fields = ["url", "keyword", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial["created"] = "2024-03-21 22:55:10"
            self.initial["modified"] = datetime.now()

    def clean_created(self):
        return self.instance.created if self.instance else None

    def clean_modified(self):
        return (
            datetime.now()
        )  # Set modified field to current datetime every time the form is submitted

    def save(self, commit=True):
        if not self.instance.pk:  # Check if instance is new
            self.instance.created = self.initial[
                "created"
            ]  # Set created field to the initial value if new
        self.instance.modified = datetime.now()  # Update modified field before saving
        return super().save(commit)
