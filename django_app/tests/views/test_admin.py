import pytest


@pytest.mark.usefixtures("alice", "bob")
def test_admin_create_location_sets_public_id(client, admin_user, django_assert_num_queries):
    client.force_login(admin_user)

    with django_assert_num_queries(1):
        response = client.get("/admin/redbox_core/user/")
    assert response.status_code == 200
