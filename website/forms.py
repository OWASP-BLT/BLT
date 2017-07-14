from django import forms
from .models import Issue, InviteFriend, UserProfile


class IssueEditForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['description', 'screenshot', 'label']


class FormInviteFriend(forms.ModelForm):
    class Meta:
        model = InviteFriend
        fields = ['recipient']
        widgets = {
            'recipient': forms.TextInput(attrs={'class': 'form-control'})
        }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('user_avatar',)
