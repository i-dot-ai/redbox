import logging
import os
from uuid import UUID

from langchain_community.embeddings import FakeEmbeddings
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings
from markitdown import MarkItDown, UnsupportedFormatException

from redbox.chains.components import get_tokeniser
from redbox_app.redbox_core.utils import sanitise_string

md = MarkItDown()
tokeniser = get_tokeniser()


def get_embedding_model():
    if "AZURE_OPENAI_API_KEY" in os.environ:
        return AzureOpenAIEmbeddings(model=EMBEDDING_MODEL)
    if "OPENAI_API_KEY" in os.environ:
        return OpenAIEmbeddings(model=EMBEDDING_MODEL)
    return FakeEmbeddings(size=3072)


def ingest(file_id: UUID) -> None:
    # These models need to be loaded at runtime otherwise they can be loaded before they exist
    from redbox_app.redbox_core.models import File, TextChunk

    file = File.objects.get(id=file_id)

    logging.info("Ingesting file: %s", file)

    try:
        markdown = md.convert(file.url)
        file.text = sanitise_string(markdown.text_content)
        file.token_count = len(tokeniser.encode(markdown.text_content))
        file.status = File.Status.complete
        file.save()

        batched_text = ["n".join(x) for x in file.text.split("\n")[::100]]

        embeddings = get_embedding_model().embed_documents(batched_text)

        for index, (batch, embedding) in enumerate(zip(batched_text, embeddings, strict=False)):
            TextChunk.objects.create(
                file=file, text=batch, index=index, embedding=embedding, token_count=len(tokeniser.encode(batch))
            )

    except (Exception, UnsupportedFormatException) as error:
        file.status = File.Status.errored
        file.ingest_error = str(error)
        file.save()
