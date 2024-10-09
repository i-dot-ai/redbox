from collections.abc import Mapping
from typing import ClassVar

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class SignInForm(forms.Form):
    email = forms.EmailField(max_length=100)


class DemographicsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("name", "ai_experience", "info_about_user", "redbox_response_preferences")
        labels: ClassVar[Mapping[str, str]] = {
            "name": "Full Name",
            "ai_experience": "How would you describe your level of experience with Generative AI tools?",
            "info_about_user": "What do you want Redbox to know about you?",
            "redbox_response_preferences": "How do you want Redbox to respond?",
        }
        widgets: ClassVar[Mapping[str, forms.Widget]] = {
            "name": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "ai_experience": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "info_about_user": forms.Textarea(attrs={"class": "govuk-textarea govuk-!-width-one-half", "rows": "5"}),
            "redbox_response_preferences": forms.Textarea(
                attrs={"class": "govuk-textarea govuk-!-width-one-half", "rows": "5"}
            ),
        }
