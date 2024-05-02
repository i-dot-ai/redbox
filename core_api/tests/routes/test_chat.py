import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompt_values import ChatPromptValue

system_chat = {"text": "test", "role": "system"}
user_chat = {"text": "test", "role": "user"}

test_history = [
    ([system_chat], 422),
    ([user_chat, system_chat], 422),
    ([system_chat, system_chat], 422),
    # ([system_chat, user_chat], 200), TODO: restore this test
]


def mock_chat_prompt(input):
    return ChatPromptValue(
        messages=[
            SystemMessage(content="You are a helpful AI bot."),
            HumanMessage(content="Hello, how are you doing?"),
        ]
    )


class MockChain:
    @staticmethod
    def stream(input):
        yield [{"input": "Test input", "text": "Test output"}]


def mock_get_chain(llm, prompt):
    return MockChain()


@pytest.mark.parametrize("chat_history, status_code", test_history)
def test_simple_chat(chat_history, status_code, app_client, monkeypatch, headers):
    monkeypatch.setattr("langchain_core.prompts.ChatPromptTemplate.from_messages", mock_chat_prompt)
    monkeypatch.setattr("core_api.src.routes.chat.LLMChain", mock_get_chain)

    response = app_client.post("/chat/vanilla", json={"message_history": chat_history}, headers=headers)
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "payload, error",
    [
        (
            [{"text": "hello", "role": "system"}],
            {"detail": "Chat history should include both system and user prompts"},
        ),
        (
            [{"text": "hello", "role": "user"}, {"text": "hello", "role": "user"}],
            {"detail": "The first entry in the chat history should be a system prompt"},
        ),
        (
            [{"text": "hello", "role": "system"}, {"text": "hello", "role": "system"}],
            {"detail": "The final entry in the chat history should be a user question"},
        ),
    ],
)
def test_chat_errors(app_client, payload, error, headers):
    """Given the app is running
    When I POST a malformed payload to /chat/vanilla
    I expect a 422 error and a meaningful message
    """
    response = app_client.post("/chat/vanilla", json={"message_history": payload}, headers=headers)
    assert response.status_code == 422
    assert response.json() == error
