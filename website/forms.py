from django import forms
from allauth.account.forms import SignupForm
from .models import InviteFriend, UserProfile, Hunt, Company
from mdeditor.fields import MDTextFormField
from captcha.fields import CaptchaField

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
    start_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'col-sm-6', 'readonly' : True}),label='', required=False ) 
    end_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'col-sm-6', 'readonly' : True}),label='', required=False)

class CaptchaForm(forms.Form):
    captcha = CaptchaField()


# class UserSignupForm(SignupForm):

#     username = forms.CharField(max_length=50,label='username')
#     email = forms.EmailField(label='email')
#     password = forms.PasswordInput()

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.errors = []

#     def is_valid(self,request):
#         if request.POST.get("password1") != request.POST.get("password2"):
#             self.errors.append("confirm password doesn't match")
        
#             self.validate_unique_email(self.email)
#             self.


class CompanySignupForm (forms.ModelForm): 
   
   class Meta:
    model = Company
    fields = (
        "admin",
        "name",
        "url",
        "email",
        "twitter",
        "facebook",
        "subscription",
        "logo"
    )
