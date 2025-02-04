import math
from datetime import UTC, datetime, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from langchain_core.documents import Document

from redbox_app.redbox_core.models import (
    ChatMessage,
    File,
    TextChunk,
)

SQRT_2_PI = math.sqrt(2.0 * math.pi)


@pytest.mark.django_db()
def test_file_model_last_referenced(chat, s3_client):  # noqa: ARG001
    mock_file = SimpleUploadedFile("test.txt", b"these are the file contents")

    new_file = File.objects.create(status=File.Status.processing, original_file=mock_file, chat=chat)

    # Tests the initial value of the last_referenced
    expected_last_referenced = new_file.created_at
    # The last_referenced should be FILE_EXPIRY_IN_SECONDS ahead of created_at
    # these fields are set during the same save() process
    # this test accounts for a delay between creating the fields
    assert abs(new_file.last_referenced - expected_last_referenced) < timedelta(seconds=1)

    # Tests that the last_referenced field can be updated
    new_date = datetime(2028, 1, 1, tzinfo=UTC)
    new_file.last_referenced = new_date
    new_file.save()
    assert new_file.last_referenced == new_date


@pytest.mark.django_db()
def test_chat_message_model_token_count_on_save(chat):
    chat_message = ChatMessage(chat=chat, role=ChatMessage.Role.ai, text="I am a message")
    assert not chat_message.token_count
    chat_message.save()
    assert chat_message.token_count == 4


def gaussian(x: float, mu: float = 0, sigma: float = 1) -> float:
    numerator = math.exp(-math.pow((x - mu) / sigma, 2) / 2)
    denominator = SQRT_2_PI * sigma
    return numerator / denominator


@pytest.mark.django()
def test_query_documents(chat, several_files):
    for file_index, file in enumerate(several_files):
        for chunk_index, text in enumerate("abc"):
            index = file_index * 3 + chunk_index
            embedding = [gaussian(i, index) for i in range(3072)]

            TextChunk.objects.create(
                text=f"{file_index}-{chunk_index}-{text}",
                index=chunk_index,
                embedding=embedding,
                token_count=10,
                file=file,
            )

    # we are going to place the question in the middle of the second file, so we expect to see
    # the first 4 files correctly re-ordered
    documents = chat.query_documents([int(i == 4) for i in range(3072)], 100)
    assert documents == [
        Document(metadata={"uri": "original_file_0.txt", "index": 0, "distance": 80}, page_content="0-0-a"),
        Document(metadata={"uri": "original_file_0.txt", "index": 1, "distance": 60}, page_content="0-1-b"),
        Document(metadata={"uri": "original_file_0.txt", "index": 2, "distance": 40}, page_content="0-2-c"),
        Document(metadata={"uri": "original_file_1.txt", "index": 0, "distance": 30}, page_content="1-0-a"),
        Document(metadata={"uri": "original_file_1.txt", "index": 1, "distance": 10}, page_content="1-1-b"),
        Document(metadata={"uri": "original_file_1.txt", "index": 2, "distance": 30}, page_content="1-2-c"),
        Document(metadata={"uri": "original_file_2.txt", "index": 0, "distance": 50}, page_content="2-0-a"),
        Document(metadata={"uri": "original_file_2.txt", "index": 1, "distance": 70}, page_content="2-1-b"),
        Document(metadata={"uri": "original_file_2.txt", "index": 2, "distance": 90}, page_content="2-2-c"),
    ]
