from unstructured.chunking.title import chunk_by_title
from unstructured.partition.auto import partition

from redbox.models import Chunk, File, Settings

env = Settings()
s3_client = env.s3_client()


def other_chunker(file: File) -> list[Chunk]:
    authenticated_s3_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": env.bucket_name, "Key": file.key},
        ExpiresIn=3600,
    )

    elements = partition(url=authenticated_s3_url)
    raw_chunks = chunk_by_title(elements=elements)

    chunks = [
        Chunk(
            parent_file_uuid=file.uuid,
            index=i,
            text=raw_chunk.text,
            metadata=raw_chunk.metadata,
            creator_user_uuid=file.creator_user_uuid,
        )
        for i, raw_chunk in enumerate(raw_chunks)
    ]

    return chunks
