import os
import platform
import re
from datetime import datetime
from email.message import Message
from email.parser import BytesParser
from typing import List, Union

from unstructured.chunking.title import chunk_by_title
from unstructured.partition.auto import partition

from redbox.models import Chunk, File


def extract_strings_from_payload(
    email: Union[Union[str, Message], List[Union[str, Message]]]
) -> List[str]:
    if isinstance(email, str):
        # If msg is a string, return a list containing the string
        return [email]
    elif isinstance(email, Message):
        # If msg is a Message object, recursively extract strings from its payload
        payload = email.get_payload()
        result = []
        if isinstance(payload, list):
            for sub_msg in payload:
                result.extend(extract_strings_from_payload(sub_msg))
        elif isinstance(payload, str):
            payload = email.get_payload(decode=True)
            try:
                # It's text
                result.append(payload.decode())
            except UnicodeDecodeError as e:
                # It's something else, like an embedded image
                print(e)
        return result


def creation_date(path_to_file):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == "Windows":
        return datetime.utcfromtimestamp(os.path.getctime(path_to_file))
    else:
        stat = os.stat(path_to_file)
        try:
            return datetime.utcfromtimestamp(stat.st_birthtime)
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return datetime.utcfromtimestamp(stat.st_mtime)


def email_chunker(file: File, creator_user_uuid="dev") -> List[Chunk]:
    with open(file.path, "r") as f:
        email = f.read()

    email_parser = BytesParser()
    messages = re.split(r"(?=^From:)", email, flags=re.M)
    messages = list(filter(None, messages))

    raw_chunks = []
    for message in messages:
        message = email_parser.parsebytes(message.encode("utf-8"))

        metadata = dict(message.items())
        metadata["parent_doc_uuid"] = file.uuid
        metadata["file_directory"] = file.path
        metadata["filename"] = file.name
        metadata["filetype"] = "message/rfc822"
        metadata["last_modified"] = (
            message.get("Date") or creation_date(file.path).isoformat()
        )

        text_list = extract_strings_from_payload(message)

        for text in text_list:
            raw_chunks.append({"metadata": metadata, "text": text})

    chunks = []
    for i, raw_chunk in enumerate(raw_chunks):
        chunk = Chunk(
            parent_file_uuid=file.uuid,
            index=i,
            text=raw_chunk["text"],
            metadata=raw_chunk["metadata"],
            creator_user_uuid=creator_user_uuid,
        )
        chunks.append(chunk)

    return chunks


def other_chunker(file: File, creator_user_uuid: str = "dev") -> List[Chunk]:
    elements = partition(filename=file.path)
    raw_chunks = chunk_by_title(elements=elements)

    chunks = []
    for i, raw_chunk in enumerate(raw_chunks):
        raw_chunk = raw_chunk.to_dict()
        raw_chunk["metadata"]["parent_doc_uuid"] = file.uuid

        chunk = Chunk(
            parent_file_uuid=file.uuid,
            index=i,
            text=raw_chunk["text"],
            metadata=raw_chunk["metadata"],
            creator_user_uuid=creator_user_uuid,
        )
        chunks.append(chunk)

    return chunks
