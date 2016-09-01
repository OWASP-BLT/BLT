from django import forms

class UploadFileForm(forms.Form):
    screenshot = forms.FileField()