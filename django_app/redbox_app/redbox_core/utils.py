from datetime import date

from django.utils import timezone


def get_date_group(on: date) -> str:
    today = timezone.now().date()
    age = (today - on).days
    if age > 30:  # noqa: PLR2004
        return "Older than 30 days"
    if age > 7:  # noqa: PLR2004
        return "Previous 30 days"
    if age > 1:
        return "Previous 7 days"
    if age > 0:
        return "Yesterday"
    return "Today"


def sanitise_string(string: str | None) -> str | None:
    """We are seeing NUL (0x00) characters in user entered fields, and also in document citations.
    We can't save these characters, so we need to sanitise them."""
    return string.replace("\x00", "\ufffd") if string else string
