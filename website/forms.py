from allauth.account.forms import SignupForm
from captcha.fields import CaptchaField
from django import forms
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
        if blurb:
            result = []
            i = 0
            while i < len(blurb):
                if blurb[i] == "<":
                    j = blurb.find(">", i)
                    if j == -1:
                        result.append(blurb[i])  # Keep the '<'
                        i += 1
                    else:
                        i = j + 1  # Skip the entire tag
                else:
                    result.append(blurb[i])
                    i += 1

            blurb = "".join(result)

            # Remove {% ... %} tags
            result = []
            i = 0
            while i < len(blurb):
                if i + 1 < len(blurb) and blurb[i : i + 2] == "{%":
                    j = blurb.find("%}", i + 2)
                    if j == -1:  # No closing tag
                        result.append(blurb[i])
                        i += 1
                    else:
                        i = j + 2  # Skip template tag
                else:
                    result.append(blurb[i])
                    i += 1

            blurb = "".join(result)

            # Remove {{ ... }} tags
            result = []
            i = 0
            while i < len(blurb):
                if i + 1 < len(blurb) and blurb[i : i + 2] == "{{":
                    j = blurb.find("}}", i + 2)
                    if j == -1:  # No closing tag
                        result.append(blurb[i])
                        i += 1
                    else:
                        i = j + 2  # Skip variable tag
                else:
                    result.append(blurb[i])
                    i += 1

            blurb = "".join(result)
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
