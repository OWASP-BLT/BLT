from django import forms
from .models import Issue


class IssueEditForm(forms.ModelForm):

    class Meta:
        model = Issue
        fields = ['description', 'screenshot']
