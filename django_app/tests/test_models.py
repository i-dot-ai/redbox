from datetime import UTC, datetime, timedelta

import pytest
from django.conf import settings
from redbox_app.redbox_core.models import File


@pytest.mark.django_db
def test_file_model_expiry_date(uploaded_file: File):
    # Tests the initial value of the expiry_date
    expected_expiry_date = uploaded_file.created_at + timedelta(seconds=settings.FILE_EXPIRY_IN_SECONDS)
    # The expiry_date should be FILE_EXPIRY_IN_SECONDS ahead of created_at
    # these fields are set during the same save() process
    # this test accounts for a delay between creating the fields
    assert abs(uploaded_file.expiry_date - expected_expiry_date) < timedelta(seconds=1)

    # Tests that the expiry_date can be updated
    new_date = datetime(2028, 1, 1, tzinfo=UTC)
    uploaded_file.expiry_date = new_date
    uploaded_file.save()
    assert uploaded_file.expiry_date == new_date
