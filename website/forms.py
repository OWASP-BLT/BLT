from captcha.fields import CaptchaField
from django import forms
from mdeditor.fields import MDTextFormField

from .models import UserProfile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("user_avatar",)

class UserDeactivateForm(forms.Form):
    deactivate = forms.BooleanField(required=True)


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
