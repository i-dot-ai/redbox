import furl
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from . import models


def _strip_microseconds(dt):
    if not dt:
        return None
    return dt.replace(microsecond=0, tzinfo=None)


class EmailVerifyTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        login_timestamp = _strip_microseconds(user.last_login)
        token_timestamp = _strip_microseconds(user.last_token_sent_at)
        return f"{user.id}{timestamp}{login_timestamp}{user.email}{token_timestamp}"


EMAIL_VERIFY_TOKEN_GENERATOR = EmailVerifyTokenGenerator()
PASSWORD_RESET_TOKEN_GENERATOR = PasswordResetTokenGenerator()


EMAIL_MAPPING = {
    "email-verification": {
        "subject": "Confirm your email address",
        "template_name": "email/verification.txt",
        "url_name": "verify-email",
        "token_generator": EMAIL_VERIFY_TOKEN_GENERATOR,
    },
    "email-register": {
        "subject": "Confirm your email address",
        "template_name": "email/verification.txt",
        "url_name": "verify-email-register",
        "token_generator": EMAIL_VERIFY_TOKEN_GENERATOR,
    },
}


def _make_token_url(user, token_type):
    token_generator = EMAIL_MAPPING[token_type]["token_generator"]
    user.last_token_sent_at = timezone.now()
    user.save()
    token = token_generator.make_token(user)
    base_url = settings.BASE_URL
    url_path = reverse(EMAIL_MAPPING[token_type]["url_name"])
    url = str(
        furl.furl(
            url=base_url,
            path=url_path,
            query_params={"code": token, "user_id": str(user.id)},
        )
    )
    return url


def _send_token_email(user, token_type):
    url = _make_token_url(user, token_type)
    context = dict(user=user, url=url, contact_address=settings.CONTACT_EMAIL)
    body = render_to_string(EMAIL_MAPPING[token_type]["template_name"], context)
    response = send_mail(
        subject=EMAIL_MAPPING[token_type]["subject"],
        message=body,
        from_email=settings.FROM_EMAIL,
        recipient_list=[user.email],
    )
    return response


def _send_normal_email(subject, template_name, to_address, context):
    body = render_to_string(template_name, context)
    response = send_mail(
        subject=subject,
        message=body,
        from_email=settings.FROM_EMAIL,
        recipient_list=[to_address],
    )
    return response


def send_password_reset_email(user):
    return _send_token_email(user, "password-reset")


def send_invite_email(user):
    user.invited_at = timezone.now()
    user.save()
    return _send_token_email(user, "invite-user")


def send_verification_email(user):
    return _send_token_email(user, "email-verification")


def send_register_email(user):
    return _send_token_email(user, "email-register")


def send_account_already_exists_email(user):
    data = EMAIL_MAPPING["account-already-exists"]
    base_url = settings.BASE_URL
    reset_url = furl.furl(url=base_url)
    reset_url.path.add(data["url_name"])
    reset_url = str(reset_url)
    context = {
        "contact_address": settings.CONTACT_EMAIL,
        "url": base_url,
        "reset_link": reset_url,
    }
    response = _send_normal_email(
        subject=data["subject"],
        template_name=data["template_name"],
        to_address=user.email,
        context=context,
    )
    return response


def verify_token(user_id, token, token_type):
    user = models.User.objects.get(id=user_id)
    result = EMAIL_MAPPING[token_type]["token_generator"].check_token(user, token)
    return result
