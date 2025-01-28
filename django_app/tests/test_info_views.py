from bs4 import BeautifulSoup
from django.test import Client


def test_support_view_contains_contact_email(client: Client):
    # When
    response = client.get("/support/")

    # Then
    soup = BeautifulSoup(response.content)
    mailto_links = [
        a.get("href", "").removeprefix("mailto:") for a in soup.find_all("a") if a.get("href", "").startswith("mailto:")
    ]
    assert mailto_links
