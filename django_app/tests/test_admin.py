import logging

import pytest
from django.contrib.auth import get_user_model

from redbox_app.redbox_core.models import ChatMessage
from redbox_app.redbox_core.serializers import ChatMessageSerializer, ChatSerializer, UserSerializer

User = get_user_model()

logger = logging.getLogger(__name__)


@pytest.mark.django_db()
def test_message_serializer(chat_message_with_citation_and_tokens: ChatMessage):
    expected = {
        "rating": 3,
        "rating_chips": ["apple", "pear"],
        "rating_text": "not bad",
        "role": "ai",
        "route": "chat",
        "selected_files": [],
        "text": "An answer.",
    }

    expected_token_usage = [
        {"use_type": "input", "model_name": "gpt-4o", "token_count": 20},
        {"use_type": "output", "model_name": "gpt-4o", "token_count": 200},
    ]

    actual = ChatMessageSerializer().to_representation(chat_message_with_citation_and_tokens)
    for k, v in expected.items():
        assert actual[k] == v, k

    for k, v in expected_token_usage[0].items():
        assert actual["token_use"][0][k] == v, k

    for k, v in expected_token_usage[1].items():
        assert actual["token_use"][1][k] == v, k


@pytest.mark.django_db()
def test_chat_serializer(chat_message_with_citation: ChatMessage):
    expected = {"name": "A chat"}
    actual = ChatSerializer().to_representation(chat_message_with_citation.chat)
    for k, v in expected.items():
        assert actual[k] == v, k
    assert actual["messages"][0]["text"]


@pytest.mark.django_db()
def test_user_serializer(chat_message_with_citation: ChatMessage):
    expected = {
        "ai_experience": "Experienced Navigator",
        "business_unit": "Government Business Services",
        "email": "alice@cabinetoffice.gov.uk",
        "grade": "D",
        "is_staff": False,
        "profession": "IA",
    }
    actual = UserSerializer().to_representation(chat_message_with_citation.chat.user)
    for k, v in expected.items():
        assert actual[k] == v, k

    assert actual["chats"][0]["messages"][0]["text"] == "An answer."
