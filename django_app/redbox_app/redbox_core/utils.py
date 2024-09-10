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


def parse_page_number(obj: int | list[int] | None) -> list[int]:
    if isinstance(obj, int):
        return [obj]
    if isinstance(obj, list) and all(isinstance(item, int) for item in obj):
        return obj
    if obj is None:
        return []

    msg = "expected, int | list[int] | None got %s"
    raise ValueError(msg, type(obj))
