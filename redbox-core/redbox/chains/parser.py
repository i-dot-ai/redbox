from collections.abc import AsyncIterator
from typing import Any, Iterator, Union
import json

from langchain_core.output_parsers import BaseCumulativeTransformOutputParser
from langchain_core.output_parsers.format_instructions import JSON_FORMAT_INSTRUCTIONS
from langchain_core.messages import BaseMessage, BaseMessageChunk
from langchain_core.outputs import ChatGenerationChunk, GenerationChunk
from langchain_core.callbacks.manager import dispatch_custom_event
from langchain_core.utils.json import parse_json_markdown
from pydantic import BaseModel


from redbox.models.graph import RedboxEventType


class StreamingJsonOutputParser(BaseCumulativeTransformOutputParser[Any]):
    """
    A Pydantic output parser which emits token events for a given field from the JSON intermediate stage.
    This allows streaming a field (answer) while maintaining the Pydantic object through the pipeline for tracking
    citations.

    This class is mostly based on existing implementations in BaseCumulativeTransformOutputParser and JsonOutputParser.
    This custom parser is here to allow emitting custom events and maintaining state for each parse, every invocation of the
    parser tracks the current length of the answer field to allow emitting delta token events.
    """

    diff: bool = False  # Ignored
    name_of_streamed_field: str = "answer"
    pydantic_schema_object: type[BaseModel]

    def parse_partial_json(self, text: str):
        try:
            return parse_json_markdown(text)
        except json.JSONDecodeError:
            return None

    def _to_generation_chunk(self, chunk: Union[str, BaseMessage]):
        chunk_gen: Union[GenerationChunk, ChatGenerationChunk]
        if isinstance(chunk, BaseMessageChunk):
            chunk_gen = ChatGenerationChunk(message=chunk)
        elif isinstance(chunk, BaseMessage):
            chunk_gen = ChatGenerationChunk(message=BaseMessageChunk(**chunk.model_dump()))
        else:
            chunk_gen = GenerationChunk(text=chunk)
        return chunk_gen

    def _transform(self, input: Iterator[Union[str, BaseMessage]]) -> Iterator[Any]:
        acc_gen: Union[GenerationChunk, ChatGenerationChunk, None] = None
        field_length_at_last_run: int = 0
        parsed = None
        for chunk in input:
            chunk_gen = self._to_generation_chunk(chunk)
            acc_gen = chunk_gen if acc_gen is None else acc_gen + chunk_gen  # type: ignore[operator]

            if parsed := self.parse_partial_json(acc_gen.text):
                if field_content := parsed.get(self.name_of_streamed_field):
                    if new_tokens := field_content[field_length_at_last_run:]:
                        dispatch_custom_event(RedboxEventType.response_tokens, data=new_tokens)
                        field_length_at_last_run = len(field_content)
                        yield self.pydantic_schema_object.model_validate(parsed)
        if parsed:
            yield self.pydantic_schema_object.model_validate(parsed)

    async def _atransform(self, input: AsyncIterator[Union[str, BaseMessage]]) -> AsyncIterator[Any]:
        acc_gen: Union[GenerationChunk, ChatGenerationChunk, None] = None
        field_length_at_last_run: int = 0
        parsed = None
        async for chunk in input:
            chunk_gen = self._to_generation_chunk(chunk)
            acc_gen = chunk_gen if acc_gen is None else acc_gen + chunk_gen  # type: ignore[operator]

            if parsed := self.parse_partial_json(acc_gen.text):
                if field_content := parsed.get(self.name_of_streamed_field):
                    if new_tokens := field_content[field_length_at_last_run:]:
                        dispatch_custom_event(RedboxEventType.response_tokens, data=new_tokens)
                        field_length_at_last_run = len(field_content)
                        yield self.pydantic_schema_object.model_validate(parsed)
        if parsed:
            yield self.pydantic_schema_object.model_validate(parsed)

    @property
    def _type(self) -> str:
        return "streaming_json_output_parser"

    def get_format_instructions(self) -> str:
        """Return the format instructions for the JSON output.

        Returns:
            The format instructions for the JSON output.
        """
        if self.pydantic_schema_object is None:
            return "Return a JSON object."
        else:
            # Copy schema to avoid altering original Pydantic schema.
            schema = dict(self.pydantic_schema_object.model_json_schema().items())

            # Remove extraneous fields.
            reduced_schema = schema
            if "title" in reduced_schema:
                del reduced_schema["title"]
            if "type" in reduced_schema:
                del reduced_schema["type"]
            # Ensure json in context is well-formed with double quotes.
            schema_str = json.dumps(reduced_schema)
            return JSON_FORMAT_INSTRUCTIONS.format(schema=schema_str)

    def parse(self, text: str) -> Any:
        return super().parse(text)
