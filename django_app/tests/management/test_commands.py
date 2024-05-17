from datetime import datetime, timedelta
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from magic_link.models import MagicLink
from redbox_app.redbox_core.models import User


@pytest.mark.django_db
def test_command_output_no_such_user():
    # Given

    # When
    with pytest.raises(CommandError) as exception:
        call_command("show_magiclink_url", "alice@example.com")

    # Then
    assert str(exception.value) == "No User found with email alice@example.com"


@pytest.mark.django_db
def test_command_output_no_links_ever(alice: User):
    # Given

    # When
    with pytest.raises(CommandError) as exception:
        call_command("show_magiclink_url", alice.email)

    # Then
    assert str(exception.value) == f"No MagicLink found for user {alice.email}"


@pytest.mark.django_db
def test_command_output_no_valid_links(alice: User):
    # Given
    MagicLink.objects.create(user=alice, expires_at=datetime.now() - timedelta(seconds=10))

    # When
    with pytest.raises(CommandError) as exception:
        call_command("show_magiclink_url", alice.email)

    # Then
    assert str(exception.value) == f"No active link for user {alice.email}"


@pytest.mark.django_db
def test_command_output_with_valid_links(alice: User):
    # Given
    link: MagicLink = MagicLink.objects.create(user=alice, expires_at=datetime.now() + timedelta(seconds=10))
    out, err = StringIO(), StringIO()

    # When
    call_command("show_magiclink_url", alice.email, stdout=out, stderr=err)

    # Then
    assert out.getvalue().strip() == link.get_absolute_url()
