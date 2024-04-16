# `Chunk`

The `Chunk` model is closely related to the `File` model. It is used to store the actual data of a file in chunks. This is done to allow the Large Language Models to process the data in smaller sections.

The `embedding` field is used to store the text embedding of the chunk, which is crucial to the vector search functionality.

Each chunk references the `File` it belongs to using the `parent_file_uuid` field.

::: redbox.models.file.Chunk

# `ChunkStatus`

The `Chunk` model also has a companion `ChunkStatus` model that helps track the status of the chunk processing. This includes information about the embedding process.

::: redbox.models.file.ChunkStatus
