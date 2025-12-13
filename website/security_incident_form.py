from django import forms

from website.models import SecurityIncident


class SecurityIncidentForm(forms.ModelForm):
    class Meta:
        model = SecurityIncident
        fields = [
            "title",
            "severity",
            "status",
            "affected_systems",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter incident title",
                }
            ),
            "severity": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "affected_systems": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "List affected systems (comma-separated)",
                    "rows": 4,
                }
            ),
        }

    def clean_affected_systems(self):
        """Optional: normalize comma-separated list."""
        value = self.cleaned_data.get("affected_systems", "")
        if value:
            return value.strip()
        return value
