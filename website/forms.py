from django import forms

from .models import InviteFriend, UserProfile, Hunt
from mdeditor.fields import MDTextFormField
from bootstrap_datepicker_plus import DateTimePickerInput


class FormInviteFriend(forms.ModelForm):
    class Meta:
        model = InviteFriend
        fields = ['recipient']
        widgets = {'recipient': forms.TextInput(attrs={'class': 'form-control'})}


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('user_avatar',)

class HuntForm (forms.Form):
    content = MDTextFormField ()

class DateTimeForm(forms.Form):
    start_date = forms.DateTimeField(
        widget=DateTimePickerInput())