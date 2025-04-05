from allauth.account.forms import SignupForm
from captcha.fields import CaptchaField
from django import forms
from django.db.models import Q
from mdeditor.fields import MDTextFormField

from website.models import (
    Bid,
    Hackathon,
    HackathonPrize,
    HackathonSponsor,
    IpReport,
    Monitor,
    Organization,
    Repo,
    Room,
    UserProfile,
)


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
    delete = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(
            attrs={
                "class": "h-5 w-5 text-[#e74c3c] border-gray-300 rounded focus:ring-[#e74c3c]",
            }
        ),
    )


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
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self, request):
        user = super().save(request)
        return user


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


class GitHubIssueForm(forms.Form):
    github_url = forms.URLField(
        label="GitHub Issue URL",
        widget=forms.URLInput(
            attrs={
                "class": "w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring focus:ring-[#e74c3c] focus:ring-opacity-50",
                "placeholder": "https://github.com/owner/repo/issues/123",
            }
        ),
        help_text=("Enter the full URL to the GitHub issue with a bounty label " "(containing a $ sign)"),
    )

    def clean_github_url(self):
        url = self.cleaned_data.get("github_url")

        # Validate that it's a GitHub URL
        if not url.startswith("https://github.com/") or "/issues/" not in url:
            raise forms.ValidationError(
                "Please enter a valid GitHub issue URL (https://github.com/owner/repo/issues/number)"
            )

        # Extract parts from the URL
        parts = url.split("/")
        if len(parts) < 7:
            raise forms.ValidationError("Invalid GitHub issue URL format")

        # Validate that the URL points to an issue, not a PR
        try:
            issue_number = int(parts[6])
            # We don't use issue_number further, but this validates it's an integer
            if issue_number <= 0:
                raise forms.ValidationError("Issue number must be positive")
        except ValueError:
            raise forms.ValidationError("Invalid issue number in URL")

        return url


class HackathonForm(forms.ModelForm):
    class Meta:
        model = Hackathon
        fields = [
            "name",
            "description",
            "organization",
            "start_time",
            "end_time",
            "banner_image",
            "rules",
            "registration_open",
            "max_participants",
            "repositories",
            "sponsor_note",
            "sponsor_link",
        ]
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "class": "w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring focus:ring-[#e74c3c] focus:ring-opacity-50",
                }
            ),
            "rules": forms.Textarea(
                attrs={
                    "rows": 5,
                    "class": "w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring focus:ring-[#e74c3c] focus:ring-opacity-50",
                }
            ),
            "sponsor_note": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring focus:ring-[#e74c3c] focus:ring-opacity-50",
                    "placeholder": "Provide information about sponsorship opportunities for this hackathon",
                }
            ),
            "sponsor_link": forms.URLInput(
                attrs={
                    "class": "w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring focus:ring-[#e74c3c] focus:ring-opacity-50",
                    "placeholder": "https://example.com/sponsor",
                }
            ),
            "start_time": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring focus:ring-[#e74c3c] focus:ring-opacity-50",
                }
            ),
            "end_time": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring focus:ring-[#e74c3c] focus:ring-opacity-50",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Filter organizations to only show those where the user is an admin or manager
        if user:
            self.fields["organization"].queryset = Organization.objects.filter(
                Q(admin=user) | Q(managers=user)
            ).distinct()

            # Filter repositories based on the selected organization
            if self.instance.pk and self.instance.organization:
                # When editing, show all repositories from the organization
                self.fields["repositories"].queryset = Repo.objects.filter(organization=self.instance.organization)
            else:
                # When creating new, start with empty queryset
                self.fields["repositories"].queryset = Repo.objects.none()


class HackathonSponsorForm(forms.ModelForm):
    class Meta:
        model = HackathonSponsor
        fields = ["organization", "sponsor_level", "logo", "website"]


class HackathonPrizeForm(forms.ModelForm):
    class Meta:
        model = HackathonPrize
        fields = ["position", "title", "description", "value", "sponsor"]
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring focus:ring-[#e74c3c] focus:ring-opacity-50",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        hackathon = kwargs.pop("hackathon", None)
        super().__init__(*args, **kwargs)

        # Filter sponsors to only show those associated with this hackathon
        if hackathon:
            self.fields["sponsor"].queryset = HackathonSponsor.objects.filter(hackathon=hackathon)
        else:
            self.fields["sponsor"].queryset = HackathonSponsor.objects.none()
