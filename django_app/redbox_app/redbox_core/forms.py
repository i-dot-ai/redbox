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
        fields = ("name", "ai_experience", "business_unit", "grade", "profession")
        labels: ClassVar[Mapping[str, str]] = {
            "name": "Full Name",
            "ai_experience": "How would you describe your level of experience with Generative AI tools?",
            "business_unit": "Business unit",
            "grade": "Grade",
            "profession": "Profession",
        }
        widgets: ClassVar[Mapping[str, forms.Widget]] = {
            "name": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "ai_experience": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "business_unit": forms.Select(attrs={"class": "govuk-select govuk-!-width-one-third"}),
            "grade": forms.Select(attrs={"class": "govuk-select govuk-!-width-one-third"}),
            "profession": forms.Select(attrs={"class": "govuk-select govuk-!-width-one-third"}),
        }
