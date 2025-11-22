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
    Job,
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
                # When creating new, start with empty queryset
                self.fields["repositories"].queryset = Repo.objects.none()

    def clean_repositories(self):
        repositories = self.cleaned_data.get("repositories")
        organization = self.cleaned_data.get("organization")

        if repositories and organization:
            # Ensure all repositories belong to the selected organization
            valid_repos = Repo.objects.filter(id__in=[r.id for r in repositories], organization=organization)
            return valid_repos
        return repositories


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


class JobForm(forms.ModelForm):
    """Form for creating and editing job postings"""

    class Meta:
        model = Job
        fields = [
            "title",
            "description",
            "requirements",
            "location",
            "job_type",
            "salary_range",
            "is_public",
            "status",
            "expires_at",
            "application_email",
            "application_url",
            "application_instructions",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "placeholder": "e.g., Senior Software Engineer",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "rows": 6,
                    "placeholder": "Describe the job role and responsibilities...",
                }
            ),
            "requirements": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "rows": 5,
                    "placeholder": "List required skills, experience, and qualifications...",
                }
            ),
            "location": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "placeholder": "e.g., Remote, New York, or Hybrid",
                }
            ),
            "job_type": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent"
                }
            ),
            "salary_range": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "placeholder": "e.g., $80k-$120k, Competitive",
                }
            ),
            "application_email": forms.EmailInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "placeholder": "careers@company.com",
                }
            ),
            "application_url": forms.URLInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "placeholder": "https://company.com/apply",
                }
            ),
            "application_instructions": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "rows": 3,
                    "placeholder": "How should candidates apply? Any special instructions...",
                }
            ),
            "is_public": forms.CheckboxInput(
                attrs={"class": "h-4 w-4 text-[#e74c3c] focus:ring-[#e74c3c] border-gray-300 rounded"}
            ),
            "status": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent"
                }
            ),
            "expires_at": forms.DateTimeInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "type": "datetime-local",
                    "placeholder": "YYYY-MM-DD HH:MM",
                }
            ),
        }
        labels = {
            "title": "Job Title",
            "description": "Job Description",
            "requirements": "Requirements",
            "location": "Location",
            "job_type": "Job Type",
            "salary_range": "Salary Range",
            "is_public": "Make this job posting public",
            "status": "Job Status",
            "expires_at": "Expiration Date",
            "application_email": "Application Email",
            "application_url": "Application URL",
            "application_instructions": "Application Instructions",
        }
        help_texts = {
            "is_public": "Public jobs can be seen by anyone, even if your organization is private",
            "status": "Draft jobs are not visible to anyone. Active jobs can receive applications. Paused jobs are visible but cannot receive applications.",
            "expires_at": "Optional: Date and time when this job posting will automatically expire",
            "application_email": "Optional: Email address where applications should be sent",
            "application_url": "Optional: Link to external application page",
            "application_instructions": "Optional: Custom instructions for applicants",
        }
