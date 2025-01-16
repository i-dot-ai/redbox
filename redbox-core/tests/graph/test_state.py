from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from redbox.models.chain import (
    LLMCallMetadata,
    RequestMetadata,
    metadata_reducer,
)

GROUP_IDS = [uuid4() for _ in range(4)]
DOCUMENT_IDS = [uuid4() for _ in range(10)]


now = datetime.now(UTC)
GPT_4o_multiple_calls_1 = [
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=0, output_tokens=0, timestamp=now - timedelta(days=10)),
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=10, output_tokens=10, timestamp=now - timedelta(days=9)),
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=10, output_tokens=10, timestamp=now - timedelta(days=8)),
]

GPT_4o_multiple_calls_1a = GPT_4o_multiple_calls_1 + [
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=50, output_tokens=50, timestamp=now - timedelta(days=7)),
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=60, output_tokens=60, timestamp=now - timedelta(days=6)),
]

GPT_4o_multiple_calls_2 = [
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=100, output_tokens=200, timestamp=now - timedelta(days=5)),
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=0, output_tokens=10, timestamp=now - timedelta(days=4)),
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=100, output_tokens=210, timestamp=now - timedelta(days=3)),
]

multiple_models_multiple_calls_1 = [
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=100, output_tokens=200, timestamp=now - timedelta(days=2)),
    LLMCallMetadata(llm_model_name="gpt-3.5", input_tokens=20, output_tokens=20, timestamp=now - timedelta(days=1)),
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=100, output_tokens=210, timestamp=now - timedelta(hours=10)),
]

multiple_models_multiple_calls_1a = multiple_models_multiple_calls_1 + [
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=300, output_tokens=310, timestamp=now - timedelta(hours=1)),
]


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1),
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_2),
            RequestMetadata(
                llm_calls=sorted(GPT_4o_multiple_calls_1 + GPT_4o_multiple_calls_2, key=lambda c: c.timestamp)
            ),
        ),
        (
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1),
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1a),
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1a),
        ),
        (
            RequestMetadata(llm_calls=multiple_models_multiple_calls_1),
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_2),
            RequestMetadata(
                llm_calls=sorted(GPT_4o_multiple_calls_2 + multiple_models_multiple_calls_1, key=lambda c: c.timestamp)
            ),
        ),
        (
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1),
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1a),
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1a),
        ),
    ],
)
def test_metadata_reducer(a: RequestMetadata, b: RequestMetadata, expected: RequestMetadata):
    result = metadata_reducer(a, b)
    assert result == expected, f"Expected: {expected}. Result: {result}"
