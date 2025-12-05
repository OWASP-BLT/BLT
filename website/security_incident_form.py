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
            "description",
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
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Detailed description of the incident",
                    "rows": 6,
                }
            ),
        }

    def clean_affected_systems(self):
        """Normalize comma-separated affected_systems (strip items, drop empties)."""
        raw = self.cleaned_data.get("affected_systems", "") or ""
        parts = [p.strip() for p in raw.split(",")]
        normalized = ", ".join(p for p in parts if p)
        return normalized
