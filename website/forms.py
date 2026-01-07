import pytz
from allauth.account.forms import SignupForm
from captcha.fields import CaptchaField
from django import forms
from django.db import transaction
from django.db.models import Q
from django.contrib.auth import get_user_model
from mdeditor.fields import MDTextFormField

from website.models import (
    Bid, Issue, Hackathon, HackathonPrize, HackathonSponsor,
    IpReport, Job, Monitor, Organization, ReminderSettings,
    Repo, Room, UserProfile,
)

User = get_user_model()

class UserProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = UserProfile
        fields = [
            "user_avatar", "description", "issues_hidden", "btc_address",
            "bch_address", "eth_address", "tags", "subscribed_domains",
            "subscribed_users", "linkedin_url", "x_username", "website_url",
            "discounted_hourly_rate", "github_url", "role",
        ]
        widgets = {
            "tags": forms.CheckboxSelectMultiple(),
            "subscribed_domains": forms.CheckboxSelectMultiple(),
            "subscribed_users": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields["email"].initial = self.instance.user.email

    def clean_email(self):
        email = self.cleaned_data.get("email").lower()
        user_query = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.user:
            user_query = user_query.exclude(pk=self.instance.user.pk)
        if user_query.exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.instance and self.instance.user:
            self.instance.user.email = self.cleaned_data["email"]
            if commit:
                self.instance.user.save()
        if commit:
            profile.save()
            self.save_m2m()
        return profile

class IssueForm(forms.ModelForm):
    # This is a virtual field. It must NOT be in Meta.fields.
    captcha = CaptchaField(
        label="Verify you are human",
        widget=forms.TextInput(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 rounded-lg focus:ring-2 focus:ring-[#e74c3c]",
            "placeholder": "Enter captcha characters",
        })
    )

    class Meta:
        model = Issue
        # FIX: Removed 'title', 'issue_type', and 'captcha' per bot analysis.
        # FIX: Added 'label' as the correct model field.
        fields = ["description", "label"]
        widgets = {
            "description": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-[#e74c3c]",
                "rows": 4,
            }),
            "label": forms.Select(attrs={
                "class": "w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-[#e74c3c]",
            }),
        }

class HackathonForm(forms.ModelForm):
    new_repo_urls = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 3,
            "class": "w-full rounded-lg border-gray-300 focus:ring-[#e74c3c]",
            "placeholder": "https://github.com/owner/repo\n(One URL per line)",
        }),
    )

    class Meta:
        model = Hackathon
        fields = [
            "name", "description", "organization", "start_time", "end_time",
            "banner_image", "rules", "registration_open", "max_participants",
            "repositories", "sponsor_note", "sponsor_link",
        ]
        base_style = "w-full rounded-lg border-gray-300 focus:ring-[#e74c3c] focus:ring-opacity-50"
        widgets = {
            "name": forms.TextInput(attrs={"class": base_style}),
            "organization": forms.Select(attrs={"class": base_style}),
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local", "class": base_style}),
            "end_time": forms.DateTimeInput(attrs={"type": "datetime-local", "class": base_style}),
            "registration_open": forms.CheckboxInput(attrs={"class": "h-5 w-5 text-[#e74c3c] rounded"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["organization"].queryset = Organization.objects.filter(
                Q(admin=user) | Q(managers=user)
            ).distinct()

    def clean_new_repo_urls(self):
        data = self.cleaned_data.get("new_repo_urls", "")
        urls = [u.strip() for u in data.splitlines() if u.strip()]
        for url in urls:
            if not url.startswith("https://github.com/"):
                raise forms.ValidationError(f"Invalid URL: {url}. Only GitHub URLs are permitted.")
        return urls

    @transaction.atomic
    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            repo_urls = self.cleaned_data.get("new_repo_urls", [])
            for url in repo_urls:
                repo_name = url.rstrip("/").split("/")[-1]
                repo, _ = Repo.objects.get_or_create(
                    repo_url=url,
                    defaults={"name": repo_name, "organization": instance.organization},
                )
                instance.repositories.add(repo)
        return instance

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            "title", "description", "requirements", "location", "job_type",
            "salary_range", "is_public", "status", "expires_at",
            "application_email", "application_url", "application_instructions",
        ]
        base_class = "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-[#e74c3c]"
        widgets = {
            "title": forms.TextInput(attrs={"class": base_class}),
            "description": forms.Textarea(attrs={"class": base_class, "rows": 6}),
            "expires_at": forms.DateTimeInput(attrs={"class": base_class, "type": "datetime-local"}),
            "is_public": forms.CheckboxInput(attrs={"class": "h-4 w-4 text-[#e74c3c]"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        methods = ["application_email", "application_url", "application_instructions"]
        if not any(cleaned_data.get(m) for m in methods):
            raise forms.ValidationError("You must provide at least one application method.")
        return cleaned_data
