import re

from allauth.account.forms import SignupForm
from captcha.fields import CaptchaField
from django import forms
from django.core.exceptions import ValidationError
from mdeditor.fields import MDTextFormField

from website.models import Room

from .models import Bid, IpReport, Monitor, UserProfile


class UserProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = UserProfile
        fields = [
            "user_avatar",
            "description",
            "issues_hidden",
            "btc_address",
            "bch_address",
            "eth_address",
            "tags",
            "subscribed_domains",
            "subscribed_users",
            "linkedin_url",
            "x_username",
            "website_url",
            "discounted_hourly_rate",
            "github_url",
            "role",
        ]
        widgets = {
            "tags": forms.CheckboxSelectMultiple(),
            "subscribed_domains": forms.CheckboxSelectMultiple(),
            "subscribed_users": forms.CheckboxSelectMultiple(),
        }

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     print("UserProfileForm __init__")
    #     print(self.instance)
    #     print(self.instance.user)
    #     if self.instance and self.instance.user:
    #         # Populate email from user model
    #         self.fields["email"].initial = self.instance.user.email

    # def save(self, commit=True):
    #     profile = super().save(commit=False)
    #     if commit:
    #         # Save email to User model
    #         if self.instance and self.instance.user:
    #             self.instance.user.email = self.cleaned_data["email"]
    #             self.instance.user.save()
    #         profile.save()
    #     return profile


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


class MonitorForm(forms.ModelForm):
    created = forms.DateTimeField(widget=forms.HiddenInput(), required=False, label="Created")
    modified = forms.DateTimeField(widget=forms.HiddenInput(), required=False, label="Modified")

    class Meta:
        model = Monitor
        fields = ["url", "keyword"]


class IpReportForm(forms.ModelForm):
    class Meta:
        model = IpReport
        fields = [
            "ip_address",
            "ip_type",
            "description",
            "activity_title",
            "activity_type",
        ]


class BidForm(forms.ModelForm):
    class Meta:
        model = Bid
        fields = [
            "user",
            "issue_url",
            "created",
            "modified",
            "amount_bch",
            "status",
            "pr_link",
            "bch_address",
        ]


class GitHubURLForm(forms.Form):
    github_url = forms.URLField(
        label="GitHub URL",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Add any Github URL"}),
    )


class SignupFormWithCaptcha(SignupForm, CaptchaForm):
    hidden_email = forms.EmailField(
        required=False,
        widget=forms.HiddenInput(attrs={"autocomplete": "off", "tabindex": "-1", "style": "display:none;"}),
    )

    # def clean(self):
    #     cleaned_data = super().clean()
    #     return cleaned_data

    # def save(self, request):
    #     user = super().save(request)
    #     return user

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", password):
            raise ValidationError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", password):
            raise ValidationError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", password):
            raise ValidationError("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password must contain at least one special character")
        return password

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            raise ValidationError("Please enter a valid email address")
        return email

    def clean_hidden_email(self):
        hidden_email = self.cleaned_data.get("hidden_email")
        if hidden_email:
            raise ValidationError("Bot submission detected")
        return hidden_email


class RoomForm(forms.ModelForm):
    captcha = CaptchaField(required=False)  # Will be required only for anonymous users

    class Meta:
        model = Room
        fields = ["name", "type", "custom_type", "description"]
        widgets = {
            "type": forms.Select(attrs={"onchange": "toggleCustomTypeField(this)"}),
        }

    def __init__(self, *args, **kwargs):
        is_anonymous = kwargs.pop("is_anonymous", False)
        super().__init__(*args, **kwargs)
        if is_anonymous:
            self.fields["captcha"].required = True
