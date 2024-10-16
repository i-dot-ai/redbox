from collections.abc import Mapping
from typing import ClassVar

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class SignInForm(forms.Form):
    email = forms.EmailField(max_length=100)


class SignUpForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "email",
            "business_unit",
            "role",
            "grade",
            "profession",
            "accessibility_options",
            "accessibility_categories",
            "accessibility_description",
            "digital_confidence",
            "ai_experience",
            "usage_at_work",
            "usage_outside_work",
            "how_useful",
            "redbox_tasks",
            "task_1_description",
            "task_1_regularity",
            "task_1_duration",
            "task_1_consider_using_ai",
            "task_2_description",
            "task_2_regularity",
            "task_2_duration",
            "task_2_consider_using_ai",
            "task_3_description",
            "task_3_regularity",
            "task_3_duration",
            "task_3_consider_using_ai",
            "role_regularity_summarise_large_docs",
            "role_regularity_condense_multiple_docs",
            "role_regularity_search_across_docs",
            "role_regularity_compare_multiple_docs",
            "role_regularity_specific_template",
            "role_regularity_shorten_docs",
            "role_regularity_write_docs",
            "role_duration_summarise_large_docs",
            "role_duration_condense_multiple_docs",
            "role_duration_search_across_docs",
            "role_duration_compare_multiple_docs",
            "role_duration_specific_template",
            "role_duration_shorten_docs",
            "role_duration_write_docs",
            "consent_research",
            "consent_interviews",
            "consent_feedback",
            "consent_condfidentiality",
            "consent_understand",
            "consent_agreement",
        )
        labels: ClassVar[Mapping[str, str]] = {
            "email": "Email address (required)",
            "business_unit": "What Business Unit are you part of",
            "role": "What's your role?",
            "grade": "What Grade (or equivalent) are you?",
            "profession": "What profession do you most identify with?",
            "accessibility_options": "Do you have any conditions or disabilities which may have an impact on your day to day life?",  # noqa: E501
            "accessibility_categories": "If you answered 'yes', which of the following categories would you class yourself in?",  # noqa: E501
            "accessibility_description": "How do these conditions or disabilities affect your use of technology and/or online services?",  # noqa: E501
            "digital_confidence": "Which statement best describes you?",
            "ai_experience": "Which statement best describes your level of experience with Generative AI (GenAI)?",
            "usage_at_work": "At WORK, how often have you used GenAI like ChatGPT, Claude or Gemini?",
            "usage_outside_work": "OUTSIDE of work, how often have you used GenAI like ChatGPT, Claude or Gemini?",
            "how_useful": "How useful have you found GenAI?",
            "redbox_tasks": "What tasks are you hoping to use Redbox for?",
            "task_1_description": "Task 1: Please describe the task",
            "task_1_regularity": "Task 1: How often do you do this?",
            "task_1_duration": "Task 1: How long does it take you to do this?",
            "task_1_consider_using_ai": "Task 1: Would you consider using GenAI to assist you with this?",
            "task_2_description": "Task 2: Please describe the task",
            "task_2_regularity": "Task 2: How often do you do this?",
            "task_2_duration": "Task 2: How long does it take you to do this?",
            "task_2_consider_using_ai": "Task 2: Would you consider using GenAI to assist you with this?",
            "task_3_description": "Task 3: Please describe the task",
            "task_3_regularity": "Task 3: How often do you do this?",
            "task_3_duration": "Task 3: How long does it take you to do this?",
            "task_3_consider_using_ai": "Task 3: Would you consider using GenAI to assist you with this?",
            "role_regularity_summarise_large_docs": "How often do you: Summarise large documents (50+ pages)",
            "role_regularity_condense_multiple_docs": "How often do you: Condense multiple documents into one summary",
            "role_regularity_search_across_docs": "How often do you: Search across many documents to answer a question",
            "role_regularity_compare_multiple_docs": "How often do you: Compare the same information across multiple documents",  # noqa: E501
            "role_regularity_specific_template": "How often do you: Write documents in a specific template, style or format",  # noqa: E501
            "role_regularity_shorten_docs": "How often do you: Edit draft documents to shorten or simplify",
            "role_regularity_write_docs": "How often do you: Write documents to facilitate meetings (chair briefs, agendas, minutes)",  # noqa: E501
            "role_duration_summarise_large_docs": "How much time to you spend on: Summarise large documents (50+ pages)",  # noqa: E501
            "role_duration_condense_multiple_docs": "How much time to you spend on: Condense multiple documents into one summary",  # noqa: E501
            "role_duration_search_across_docs": "How much time to you spend on: Search across many documents to answer a question",  # noqa: E501
            "role_duration_compare_multiple_docs": "How much time to you spend on: Compare the same information across multiple documents",  # noqa: E501
            "role_duration_specific_template": "How much time to you spend on: Write documents in a specific template, style or format",  # noqa: E501
            "role_duration_shorten_docs": "How much time to you spend on: Edit draft documents to shorten or simplify",
            "role_duration_write_docs": "How much time to you spend on: Write documents to facilitate meetings (chair briefs, agendas, minutes)",  # noqa: E501
            "consent_research": "I agree to take part in research (required)",
            "consent_interviews": "I agree to take part in interviews and group sessions (required)",
            "consent_feedback": "I agree for the i.AI to share my anonymised feedback with others (required)",
            "consent_condfidentiality": "Confidential - I understand that the ideas, designs and services I see are confidential as part of the user testing of Ask AI. I will not tell anyone else about the ideas, designs or services until they are made public. I will not take away copies of any materials I use in the session. (required)",  # noqa: E501
            "consent_understand": "I understand my participation in this research (required)",
            "consent_agreement": "I give my informed, voluntary consent to take part in this research as per my selections above (required)",  # noqa: E501
        }
        widgets: ClassVar[Mapping[str, forms.Widget]] = {
            "email": forms.EmailInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "business_unit": forms.Select(attrs={"class": "govuk-select"}),
            "role": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "grade": forms.Select(attrs={"class": "govuk-select"}),
            "profession": forms.Select(attrs={"class": "govuk-select"}),
            "accessibility_options": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "accessibility_categories": forms.TextInput(attrs={"class": "govuk-checkboxes__item"}),
            "accessibility_description": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "digital_confidence": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "ai_experience": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "usage_at_work": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "usage_outside_work": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "how_useful": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "redbox_tasks": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "task_1_description": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "task_1_regularity": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "task_1_duration": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "task_1_consider_using_ai": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "task_2_description": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "task_2_regularity": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "task_2_duration": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "task_2_consider_using_ai": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "task_3_description": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "task_3_regularity": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "task_3_duration": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "task_3_consider_using_ai": forms.TextInput(attrs={"class": "govuk-input govuk-!-width-one-half"}),
            "role_regularity_summarise_large_docs": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "role_regularity_condense_multiple_docs": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "role_regularity_search_across_docs": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "role_regularity_compare_multiple_docs": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "role_regularity_specific_template": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "role_regularity_shorten_docs": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "role_regularity_write_docs": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "role_duration_summarise_large_docs": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "role_duration_condense_multiple_docs": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "role_duration_search_across_docs": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "role_duration_compare_multiple_docs": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "role_duration_specific_template": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "role_duration_shorten_docs": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "role_duration_write_docs": forms.RadioSelect(attrs={"class": "govuk-radios__item"}),
            "consent_research": forms.CheckboxInput(attrs={"class": "govuk-checkboxes__input"}),
            "consent_interviews": forms.CheckboxInput(attrs={"class": "govuk-checkboxes__input"}),
            "consent_feedback": forms.CheckboxInput(attrs={"class": "govuk-checkboxes__input"}),
            "consent_condfidentiality": forms.CheckboxInput(attrs={"class": "govuk-checkboxes__input"}),
            "consent_understand": forms.CheckboxInput(attrs={"class": "govuk-checkboxes__input"}),
            "consent_agreement": forms.CheckboxInput(attrs={"class": "govuk-checkboxes__input"}),
        }


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
