from django import forms


class SignInForm(forms.Form):
    email = forms.EmailField(max_length=100)
