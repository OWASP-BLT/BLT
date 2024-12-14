from captcha.fields import CaptchaField
from django import forms
from mdeditor.fields import MDTextFormField

from .models import AdditionalRepo, Bid, IpReport, Monitor, Project, UserProfile


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


class FilterForm(forms.Form):
    activity_status = forms.MultipleChoiceField(
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "filter-select"}),
        choices=[],
    )
    project_type = forms.MultipleChoiceField(
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "filter-select"}),
        choices=[],
    )
    project_level = forms.MultipleChoiceField(
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "filter-select"}),
        choices=[],
    )

    def __init__(self, *args, **kwargs):
        super(FilterForm, self).__init__(*args, **kwargs)
        self.fields["activity_status"].choices = [
            (status, status)
            for status in Project.objects.values_list("activity_status", flat=True).distinct()
        ]
        self.fields["project_type"].choices = [
            (ptype, ptype)
            for ptype in Project.objects.values_list("project_type", flat=True).distinct()
        ]
        self.fields["project_level"].choices = [
            (level, level)
            for level in Project.objects.values_list("project_level", flat=True).distinct()
        ]


class GitHubURLForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["github_url"]
        widgets = {
            "github_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://github.com/username/repository",
                }
            )
        }


class AdditionalRepoForm(forms.ModelForm):
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(), widget=forms.Select(attrs={"class": "form-control"})
    )
    github_url = forms.URLField(
        widget=forms.URLInput(
            attrs={"class": "form-control", "placeholder": "https://github.com/username/repository"}
        )
    )

    class Meta:
        model = AdditionalRepo
        fields = ["project", "github_url"]
