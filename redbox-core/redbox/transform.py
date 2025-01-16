import tiktoken
from langchain_core.callbacks.manager import dispatch_custom_event
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from redbox.models.chain import LLMCallMetadata, RequestMetadata
from redbox.models.graph import RedboxEventType


def to_request_metadata(obj: dict) -> RequestMetadata:
    """Takes a dictionary with keys 'prompt', 'response' and 'model' and creates metadata.

    Will also emit events for metadata updates.
    """

    prompt = obj["prompt"]
    response = obj["text_and_tools"]["raw_response"].content
    model = obj["model"]

    try:
        tokeniser = tiktoken.encoding_for_model(model)
    except KeyError:
        tokeniser = tiktoken.get_encoding("cl100k_base")

    input_tokens = len(tokeniser.encode(prompt))
    output_tokens = len(tokeniser.encode(response))

    metadata_event = RequestMetadata(
        llm_calls=[
            LLMCallMetadata(
                llm_model_name=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        ]
    )

    dispatch_custom_event(RedboxEventType.on_metadata_generation.value, metadata_event)

    return metadata_event


@RunnableLambda
def get_all_metadata(obj: dict):
    text_and_tools = obj["text_and_tools"]

    if parsed_response := text_and_tools.get("parsed_response"):
        text = getattr(parsed_response, "answer", parsed_response)
        citations = getattr(parsed_response, "citations", [])
    else:
        text = text_and_tools["raw_response"].content
        citations = []

    out = {
        "messages": [AIMessage(content=text, tool_calls=text_and_tools["raw_response"].tool_calls)],
        "metadata": to_request_metadata(obj),
        "citations": citations,
    }
    return out
