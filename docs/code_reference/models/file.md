# `File`

The `File` model is the fundamental model for storing file references in the Redbox system. It maintains a lightweight reference to files location in S3.


::: redbox.models.file.File

# `FileStatus`

The `File` model also has a companion `FileStatus` model that helps track the status of the file processing. This nests `ChunkStatus` models to see if chunks have been created and if they have been completely embedded yet.

::: redbox.models.file.FileStatus