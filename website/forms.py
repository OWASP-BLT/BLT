from django import forms
from .models import Issue, InviteFriend


class IssueEditForm(forms.ModelForm):

    class Meta:
        model = Issue
        fields = ['description', 'screenshot']


class FormInviteFriend(forms.ModelForm):

    class Meta:
        model = InviteFriend
        fields = ['recipient']
        widgets = {
            'recipient': forms.TextInput(attrs={'class': 'form-control'})
        }
