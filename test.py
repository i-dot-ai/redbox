import dotenv
from langchain.chat_models import ChatAnthropic

from redbox.llm.llm_base import LLMHandler
from redbox.models.file import Chunk, File

ENV = dotenv.dotenv_values(".env")

llm = ChatAnthropic(
    anthropic_api_key=ENV["ANTHROPIC_API_KEY"],
    max_tokens=4000,
    temperature=0.8,
    streaming=True,
)


llm_handler = LLMHandler(llm=llm, user_uuid="dev")


file = File(
    path="test_file",
    type="test_file",
    name="test_file",
    storage_kind="local",
    text="This is a test file",
    classifications={},
)

test_chunk = Chunk(
    parent_file=file,
    text="This is a test chunk",
    index=1,
    metadata={},
)


llm_handler.add_chunks_to_vector_store(chunks=[test_chunk])
