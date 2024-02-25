from django import forms

from .models import UserProfile, Hunt
from mdeditor.fields import MDTextFormField
from captcha.fields import CaptchaField


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('user_avatar',)

class HuntForm (forms.Form): 
    content = MDTextFormField ()
    start_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'col-sm-6', 'readonly' : True}),label='', required=False ) 
    end_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'col-sm-6', 'readonly' : True}),label='', required=False)

class CaptchaForm(forms.Form):
    captcha = CaptchaField()

class QuickIssueForm(forms.Form):
    url = forms.CharField()
    label = forms.CharField()
    description = forms.CharField()