from datetime import date, timedelta

import pytest
from django.utils import timezone

from redbox_app.redbox_core.utils import get_date_group


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (timezone.now().date(), "Today"),
        ((timezone.now() - timedelta(days=1)).date(), "Yesterday"),
        ((timezone.now() - timedelta(days=2)).date(), "Previous 7 days"),
        ((timezone.now() - timedelta(days=7)).date(), "Previous 7 days"),
        ((timezone.now() - timedelta(days=8)).date(), "Previous 30 days"),
        ((timezone.now() - timedelta(days=30)).date(), "Previous 30 days"),
        ((timezone.now() - timedelta(days=31)).date(), "Older than 30 days"),
    ],
)
def test_date_group_calculation(given: date, expected: str):
    # Given

    # When
    actual = get_date_group(given)

    # Then
    assert actual == expected
