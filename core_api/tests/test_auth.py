from uuid import uuid4

import pytest
from jose import jwt


@pytest.mark.parametrize(
    ("malformed_headers", "status_code"),
    [
        (None, 403),
        ({"Authorization": "blah blah"}, 403),
        ({"Authorization": "Bearer blah-blah"}, 401),
        ({"Authorization": "Bearer " + jwt.encode({"user_uuid": "not a uuid"}, key="super-secure-private-key")}, 401),
        ({"Authorization": "Bearer " + jwt.encode({"user_uuid": str(uuid4())}, key="super-secure-private-key")}, 404),
    ],
)
def test_get_file_fails_auth(app_client, stored_file_1, malformed_headers, status_code):
    """
    Given a previously saved file
    When I GET it from /file/uuid with a missing/broken/correct header
    I Expect get an appropriate status_code
    """
    response = app_client.get(f"/file/{stored_file_1.uuid}", headers=malformed_headers)
    assert response.status_code == status_code
