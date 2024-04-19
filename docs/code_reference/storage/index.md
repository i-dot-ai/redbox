# Storage

The storage module provides a way to store and retrieve data from the backend database. We have abstracted it to provide a common interface to interact with the database. This allows us to switch between different databases without changing the code that interacts with the database.

## Abstract Storage

::: redbox.storage.storage_handler.BaseStorageHandler