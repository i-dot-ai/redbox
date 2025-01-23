import logging
from uuid import UUID

from markitdown import MarkItDown, UnsupportedFormatException

from redbox.chains.components import get_tokeniser
from redbox_app.redbox_core.utils import sanitise_string

md = MarkItDown()
tokeniser = get_tokeniser()


def ingest(file_id: UUID) -> None:
    # These models need to be loaded at runtime otherwise they can be loaded before they exist
    from redbox_app.redbox_core.models import File

    file = File.objects.get(id=file_id)

    logging.info("Ingesting file: %s", file)

    try:
        markdown = md.convert(file.url)
        file.text = sanitise_string(markdown.text_content)
        file.token_count = len(tokeniser.encode(markdown.text_content))
        file.status = File.Status.complete
    except (Exception, UnsupportedFormatException) as error:  # noqa: BLE001
        file.status = File.Status.errored
        file.ingest_error = str(error)
    file.save()
