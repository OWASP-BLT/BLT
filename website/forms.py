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
    Recommendation,
    RecommendationRequest,
    RecommendationSkill,
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
        help_text=("Enter the full URL to the GitHub issue with a bounty label (containing a $ sign)"),
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
                    "placeholder": ("Provide information about sponsorship opportunities for this hackathon"),
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
                    "class": ("h-5 w-5 text-[#e74c3c] focus:ring-[#e74c3c] border-gray-300 rounded"),
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


class JobForm(forms.ModelForm):
    """Form for creating and editing job postings"""

    def clean(self):
        """Validate that at least one application method is provided"""
        cleaned_data = super().clean()
        application_email = cleaned_data.get("application_email")
        application_url = cleaned_data.get("application_url")
        application_instructions = cleaned_data.get("application_instructions")

        if not any([application_email, application_url, application_instructions]):
            raise forms.ValidationError(
                "Please provide at least one way for candidates to apply (email, URL, or instructions)."
            )

        return cleaned_data

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
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "placeholder": "e.g., Senior Software Engineer",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "rows": 6,
                    "placeholder": "Describe the job role and responsibilities...",
                }
            ),
            "requirements": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "rows": 5,
                    "placeholder": "List required skills, experience, and qualifications...",
                }
            ),
            "location": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "placeholder": "e.g., Remote, New York, or Hybrid",
                }
            ),
            "job_type": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent"
                }
            ),
            "salary_range": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "placeholder": "e.g., $80k-$120k, Competitive",
                }
            ),
            "application_email": forms.EmailInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "placeholder": "careers@company.com",
                }
            ),
            "application_url": forms.URLInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "placeholder": "https://company.com/apply",
                }
            ),
            "application_instructions": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
                    "rows": 3,
                    "placeholder": "How should candidates apply? Any special instructions...",
                }
            ),
            "is_public": forms.CheckboxInput(
                attrs={
                    "class": "h-4 w-4 text-[#e74c3c] focus:ring-[#e74c3c] border-gray-300 dark:border-gray-600 dark:bg-gray-700 rounded"
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent"
                }
            ),
            "expires_at": forms.DateTimeInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent",
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


class RecommendationForm(forms.ModelForm):
    """
    Form for creating/editing user recommendations.
    """

    skills_endorsed = forms.ModelMultipleChoiceField(
        queryset=RecommendationSkill.objects.none(),  # Will be set in __init__
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        help_text="Select up to 5 skills to endorse (optional)",
    )

    class Meta:
        model = Recommendation
        fields = ["relationship", "recommendation_text"]
        # skills_endorsed is handled separately, not as a model field in the form
        widgets = {
            "relationship": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "recommendation_text": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Tell us about your experience working with this person... (minimum 200 characters)",
                    "minlength": 200,
                    "maxlength": 1000,
                    "title": "Recommendation text must be between 200 and 1000 characters",
                }
            ),
        }
        help_texts = {
            "relationship": "Select your relationship with this person",
            "recommendation_text": "Write a detailed recommendation (200-1000 characters)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up relationship field with placeholder option (but still required)
        self.fields["relationship"].required = True
        self.fields["relationship"].empty_label = "None selected"
        self.fields["relationship"].initial = None

        # Set up skills_endorsed field with checkboxes (not a model field, handled separately)
        try:
            skills_queryset = RecommendationSkill.objects.all().order_by("category", "name")
            # Group skills by category for better organization
            skills_by_category = {}
            for skill in skills_queryset:
                category = skill.category or "Other"
                if category not in skills_by_category:
                    skills_by_category[category] = []
                skills_by_category[category].append((skill.name, skill.name))

            # Create choices (no category headers for checkboxes, we'll group in template)
            choices = []
            for category in sorted(skills_by_category.keys()):
                choices.extend(skills_by_category[category])

            # Store category mapping for template use
            self.skills_by_category = skills_by_category
        except Exception:
            choices = []
            self.skills_by_category = {}

        self.fields["skills_endorsed"] = forms.MultipleChoiceField(
            choices=choices,
            required=False,
            widget=forms.CheckboxSelectMultiple(
                attrs={
                    "class": "skills-checkbox-list",
                }
            ),
            help_text="Select up to 5 skills to endorse (optional)",
        )

    def clean_recommendation_text(self):
        """Validate recommendation text length"""
        text = self.cleaned_data.get("recommendation_text", "")
        if len(text) < 200:
            raise forms.ValidationError("Recommendation text must be at least 200 characters long.")
        if len(text) > 1000:
            raise forms.ValidationError("Recommendation text must not exceed 1000 characters.")
        return text

    def clean_skills_endorsed(self):
        """Limit skills to maximum of 5 and filter out category headers"""
        skills = self.cleaned_data.get("skills_endorsed", [])
        # Filter out category headers (they start with "---")
        skills = [s for s in skills if not s.startswith("---")]
        if len(skills) > 5:
            raise forms.ValidationError("You can select a maximum of 5 skills.")
        return skills

    def save(self, commit=True):
        """Override save to convert skills to list of names for JSON storage"""
        recommendation = super().save(commit=False)
        # Convert skills to list of skill names for JSON storage (skills are already strings from MultipleChoiceField)
        skills = self.cleaned_data.get("skills_endorsed", [])
        if skills:
            # Filter out any category headers and store as list of skill names
            recommendation.skills_endorsed = [skill for skill in skills if not skill.startswith("---")]
        else:
            recommendation.skills_endorsed = []
        if commit:
            recommendation.save()
        return recommendation


class RecommendationRequestForm(forms.ModelForm):
    """
    Form for requesting a recommendation from another user.
    """

    class Meta:
        model = RecommendationRequest
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Optional: Add a personal message to your request...",
                    "maxlength": 500,
                }
            ),
        }
        help_texts = {
            "message": "Optional message to include with your request (max 500 characters)",
        }

    def clean_message(self):
        """Validate message length"""
        message = self.cleaned_data.get("message", "")
        if message and len(message) > 500:
            raise forms.ValidationError("Message must not exceed 500 characters.")
        return message


class RecommendationBlurbForm(forms.ModelForm):
    """
    Form for editing the recommendation blurb/summary on profile.
    """

    class Meta:
        model = UserProfile
        fields = ["recommendation_blurb"]
        widgets = {
            "recommendation_blurb": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Write a short summary about yourself... (max 500 characters)",
                    "maxlength": 500,
                }
            ),
        }
        help_texts = {
            "recommendation_blurb": "Short summary/about section (max 500 characters)",
        }

    def clean_recommendation_blurb(self):
        """Validate blurb length"""
        blurb = self.cleaned_data.get("recommendation_blurb", "")
        if blurb and len(blurb) > 500:
            raise forms.ValidationError("Blurb must not exceed 500 characters.")
        return blurb
