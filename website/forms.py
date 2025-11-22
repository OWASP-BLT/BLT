import pytz
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
    ReminderSettings,
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
                "class": "w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring focus:ring-[#e74c3c] focus:ring-opacity-50 bg-white dark:bg-gray-900",
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
    new_repo_urls = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": (
                    "w-full rounded-lg border-gray-300 shadow-sm focus:border-[#e74c3c] "
                    "focus:ring focus:ring-[#e74c3c] focus:ring-opacity-50"
                ),
                "placeholder": "https://github.com/owner/repo1\nhttps://github.com/owner/repo2",
            }
        ),
        label="New Repository URLs",
        help_text="Enter GitHub repository URLs (one per line) to add new repositories to this hackathon",
    )

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
        base_input_class = (
            "w-full rounded-lg border-gray-300 shadow-sm focus:border-[#e74c3c] "
            "focus:ring focus:ring-[#e74c3c] focus:ring-opacity-50"
        )
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": base_input_class,
                    "placeholder": "Enter hackathon name",
                }
            ),
            "organization": forms.Select(
                attrs={
                    "class": base_input_class,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "class": base_input_class,
                    "placeholder": "Describe your hackathon...",
                }
            ),
            "rules": forms.Textarea(
                attrs={
                    "rows": 5,
                    "class": base_input_class,
                    "placeholder": "Enter hackathon rules...",
                }
            ),
            "sponsor_note": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": base_input_class,
                    "placeholder": ("Provide information about sponsorship opportunities " "for this hackathon"),
                }
            ),
            "sponsor_link": forms.URLInput(
                attrs={
                    "class": base_input_class,
                    "placeholder": "https://example.com/sponsor",
                }
            ),
            "start_time": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": base_input_class,
                }
            ),
            "end_time": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": base_input_class,
                }
            ),
            "max_participants": forms.NumberInput(
                attrs={
                    "class": base_input_class,
                    "placeholder": "Enter maximum number of participants",
                }
            ),
            "repositories": forms.SelectMultiple(
                attrs={
                    "class": base_input_class,
                    "size": "5",
                }
            ),
            "registration_open": forms.CheckboxInput(
                attrs={
                    "class": ("h-5 w-5 text-[#e74c3c] focus:ring-[#e74c3c] " "border-gray-300 rounded"),
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
                # When creating new, try to get organization from form data
                organization_id = None
                if "data" in kwargs and kwargs["data"]:
                    organization_id = kwargs["data"].get("organization")

                if organization_id:
                    # Show repositories from the selected organization
                    self.fields["repositories"].queryset = Repo.objects.filter(organization_id=organization_id)
                else:
                    # No organization selected yet, start with empty queryset
                    self.fields["repositories"].queryset = Repo.objects.none()

    def clean_new_repo_urls(self):
        """Validate and parse new repository URLs."""
        new_repo_urls = self.cleaned_data.get("new_repo_urls", "")
        if not new_repo_urls:
            return []

        urls = [url.strip() for url in new_repo_urls.strip().split("\n") if url.strip()]
        validated_urls = []

        for url in urls:
            # Basic validation for GitHub URLs
            if not url.startswith("https://github.com/"):
                raise forms.ValidationError(f"Invalid GitHub URL: {url}. URLs must start with https://github.com/")

            # Check if URL has the correct format
            parts = url.replace("https://github.com/", "").split("/")
            if len(parts) < 2:
                raise forms.ValidationError(
                    f"Invalid GitHub URL format: {url}. Expected format: https://github.com/owner/repo"
                )

            validated_urls.append(url)

        return validated_urls

    def clean_repositories(self):
        repositories = self.cleaned_data.get("repositories")
        organization = self.cleaned_data.get("organization")

        if repositories and organization:
            # Ensure all repositories belong to the selected organization
            valid_repos = Repo.objects.filter(id__in=[r.id for r in repositories], organization=organization)
            return valid_repos
        return repositories

    def save(self, commit=True):
        """Save the hackathon and create new repositories if provided."""
        instance = super().save(commit=False)

        if commit:
            instance.save()
            # Save many-to-many relationships
            self.save_m2m()

            # Create and add new repositories
            new_repo_urls = self.cleaned_data.get("new_repo_urls", [])
            if new_repo_urls:
                organization = instance.organization
                for repo_url in new_repo_urls:
                    # Extract repo name from URL
                    repo_name = repo_url.rstrip("/").split("/")[-1]

                    # Check if repo already exists
                    existing_repo = Repo.objects.filter(repo_url=repo_url).first()
                    if existing_repo:
                        # Add existing repo to hackathon
                        instance.repositories.add(existing_repo)
                    else:
                        # Create new repo
                        new_repo = Repo.objects.create(
                            name=repo_name,
                            repo_url=repo_url,
                            organization=organization,
                        )
                        instance.repositories.add(new_repo)

        return instance


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


class ReminderSettingsForm(forms.ModelForm):
    reminder_time = forms.TimeField(
        widget=forms.TimeInput(
            attrs={
                "type": "time",
                "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring-[#e74c3c] sm:text-sm",
            },
            format="%H:%M",
        ),
        input_formats=["%H:%M", "%I:%M %p", "%H:%M:%S"],
        help_text="Select your preferred daily reminder time. Note: Notifications may be delayed by up to 15 minutes.",
    )

    timezone = forms.ChoiceField(
        choices=[(tz, tz) for tz in pytz.common_timezones],
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring-[#e74c3c] sm:text-sm"
            }
        ),
        help_text="Select your timezone",
    )

    class Meta:
        model = ReminderSettings
        fields = ["reminder_time", "timezone", "is_active"]
        widgets = {
            "is_active": forms.CheckboxInput(
                attrs={"class": "h-4 w-4 text-[#e74c3c] focus:ring-[#e74c3c] border-gray-300 rounded"}
            )
        }
