from unittest.mock import patch

import pytest
from django.urls import reverse
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage

from redbox_app.redbox_core.models import Chat


class CannedGraphLLM(BaseChatModel):
    responses: list[dict]

    def _generate(self, *_args, **_kwargs):
        yield from self.responses

    def _llm_type(self):
        return "canned"

    def invoke(self, *_args, **_kwargs) -> BaseMessage:
        return AIMessage(content=self.responses[0]["content"])


@pytest.fixture()
def mocked_connect():
    return "azure/gpt-4o", {"mock_response": "no"}


def test_post_pass(chat: Chat, mocked_connect, client):
    url = reverse("chat-message", args=(chat.id,))

    client.force_login(chat.user)

    # When
    with patch("redbox.RedboxState.get_llm", new=lambda _: mocked_connect):
        message = "write me poem"
        response = client.post(url, {"message": "write me poem"})
        assert response.status_code == 200
        assert response.json()["title"] == message
