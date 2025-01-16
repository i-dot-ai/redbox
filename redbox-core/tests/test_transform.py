from datetime import UTC, datetime

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from redbox.models.chain import LLMCallMetadata, RequestMetadata
from redbox.transform import     to_request_metadata

document_created = datetime.now(UTC)


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (
            {
                "prompt": "Lorem ipsum dolor sit amet.",
                "model": "gpt-4o",
                "text_and_tools": {
                    "raw_response": AIMessage(
                        content=(
                            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
                            "sed do eiusmod tempor incididunt ut labore et dolore magna "
                            "aliqua. "
                        )
                    )
                },
            },
            RequestMetadata(llm_calls={LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=6, output_tokens=23)}),
        ),
        (
            {
                "prompt": "Lorem ipsum dolor sit amet.",
                "model": "unknown-model",
                "text_and_tools": {
                    "raw_response": AIMessage(
                        content=(
                            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
                            "sed do eiusmod tempor incididunt ut labore et dolore magna "
                            "aliqua. "
                        )
                    )
                },
            },
            RequestMetadata(
                llm_calls={LLMCallMetadata(llm_model_name="unknown-model", input_tokens=6, output_tokens=23)}
            ),
        ),
    ],
)
def test_to_request_metadata(output: dict, expected: RequestMetadata):
    result = RunnableLambda(to_request_metadata).invoke(output)
    # We assert on token counts here as the id generation causes the LLMCallMetadata objects not to match
    assert (
        result.input_tokens == expected.input_tokens
    ), f"Expected: {expected.input_tokens} Result: {result.input_tokens}"
    assert (
        result.output_tokens == expected.output_tokens
    ), f"Expected: {expected.output_tokens} Result: {result.output_tokens}"
