from django.core.management import call_command
from django.urls import reverse


def test_download_metrics(user_with_chats_with_messages_over_time, client, alice):  # noqa: ARG001
    # Given
    client.force_login(alice)
    call_command("chat_metrics")

    #  When
    url = reverse("download-metrics")
    response = client.get(url)

    # I expect
    assert response.status_code == 200
    csv = response.content.decode().split("\n")
    header = [item.strip(' "') for item in csv[0].split(",")]
    assert header == [
        "extraction_date",
        "created_at__date",
        "business_unit",
        "grade",
        "profession",
        "ai_experience",
        "token_count__avg",
        "rating__avg",
        "delay__avg",
        "id__count",
        "n_selected_files__count",
        "chat_id__count",
        "user_id__count",
    ]

    assert len(csv) == 7
