from django import forms

from .models import InviteFriend, UserProfile


class FormInviteFriend(forms.ModelForm):
    class Meta:
        model = InviteFriend
        fields = ['recipient']
        widgets = {'recipient': forms.TextInput(attrs={'class': 'form-control'})}


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('user_avatar',)
