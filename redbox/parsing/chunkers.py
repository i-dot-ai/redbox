from unstructured.chunking.title import chunk_by_title
from unstructured.partition.auto import partition

from redbox.models import Chunk, File, Settings

env = Settings()
s3_client = env.s3_client()

def other_chunker(file: File) -> list[Chunk]:
    authenticated_s3_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": env.bucket_name, "Key": file.name},
        ExpiresIn=3600,
    )

def other_chunker(file: File) -> list[Chunk]:
    elements = partition(url=file.url)
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
            creator_user_uuid=file.creator_user_uuid,
        )
        chunks.append(chunk)

    return chunks
