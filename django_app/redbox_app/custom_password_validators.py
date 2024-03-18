import re
import string

from django.core.exceptions import ValidationError
from redbox_app.redbox_core.constants import BUSINESS_SPECIFIC_WORDS


class SpecialCharacterValidator:
    msg = "The password must contain at least one special character."

    def validate(self, password, user=None):
        special_characters = string.punctuation

        if not any(char in special_characters for char in password):
            raise ValidationError(self.msg)

    def get_help_text(self):
        return self.msg


class LowercaseUppercaseValidator:
    msg = "The password must contain at least one lowercase character and one uppercase character."

    def validate(self, password, user=None):
        contains_lowercase = any(char.islower() for char in password)
        contains_uppercase = any(char.isupper() for char in password)

        if (not contains_lowercase) or (not contains_uppercase):
            raise ValidationError(self.msg)

    def get_help_text(self):
        return self.msg


class BusinessPhraseSimilarityValidator:
    msg = "The password should not contain business specific words."

    def validate(self, password, user=None):
        password_lower = password.lower()
        for phrase in BUSINESS_SPECIFIC_WORDS:
            phrase_no_space = phrase.replace(" ", "")
            phrase_underscore = phrase.replace(" ", "_")
            phrase_dash = phrase.replace(" ", "-")
            search_phrase = "|".join([phrase_no_space, phrase_underscore, phrase_dash])
            if re.search(search_phrase, password_lower):
                raise ValidationError(self.msg)
