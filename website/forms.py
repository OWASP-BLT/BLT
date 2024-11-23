import re

from captcha.fields import CaptchaField
from django import forms
from mdeditor.fields import MDTextFormField

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
            "recommendation_blurb",
        ]
        widgets = {
            "tags": forms.CheckboxSelectMultiple(),
            "subscribed_domains": forms.CheckboxSelectMultiple(),
            "subscribed_users": forms.CheckboxSelectMultiple(),
            "recommendation_blurb": forms.Textarea(
                attrs={
                    "rows": "10",
                    "class": "mt-2 block w-full py-3 px-4 text-base border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
                    "placeholder": "Write your recommendation blurb here...",
                }
            ),
        }

    def clean_recommendation_blurb(self):
        blurb = self.cleaned_data.get("recommendation_blurb")
        # Remove any potential template tags or code that might have been entered
        if blurb:
            # Remove any HTML or template tags
            blurb = re.sub(r"<[^>]+>", "", blurb)
            blurb = re.sub(r"{%.*?%}", "", blurb)
            blurb = re.sub(r"{{.*?}}", "", blurb)
        return blurb

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
        fields = ["ip_address", "ip_type", "description", "activity_title", "activity_type"]


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
