from unittest.mock import patch

import pytest
from django.urls import reverse
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessageChunk
from pydantic import BaseModel

from redbox_app.redbox_core.models import Chat


class CannedGraphLLM(BaseChatModel):
    responses: list[dict]

    def _generate(self, *_args, **_kwargs):
        for _ in self.responses:
            yield

    def _llm_type(self):
        return "canned"

    async def astream_events(self, *_args, **_kwargs):
        for response in self.responses:
            yield response


class Token(BaseModel):
    content: str


@pytest.fixture()
def mocked_connect():
    responses = [
        {
            "event": "on_chat_model_stream",
            "data": {"chunk": Token(content="Good afternoon, ")},
        },
        {"event": "on_chat_model_stream", "data": {"chunk": Token(content="Mr. Amor.")}},
        {
            "event": "on_chain_end",
            "data": {"output": AIMessageChunk(content="Good afternoon, Mr. Amor.")},
        },
    ]

    return CannedGraphLLM(responses=responses)


def test_post_pass(chat: Chat, mocked_connect, client):
    url = reverse("chat-message", args=(chat.id,))

    client.force_login(chat.user)

    # When
    with patch(
        "redbox_app.redbox_core.views.api_views.ChatMessageView.redbox._get_runnable", new=lambda _: mocked_connect
    ):
        response = client.post(url, {"message": "write me poem"})
        assert response.status_code == 200
        assert response.json() == {}
