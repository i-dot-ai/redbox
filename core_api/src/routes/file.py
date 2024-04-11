from uuid import UUID

from fastapi import HTTPException
from pydantic import AnyHttpUrl

from core_api.src.routes.sub_app import SubApp
from redbox.models import Chunk, File, FileStatus


class FileSubApp(SubApp):
    def __init__(self, router, storage_handler, log, publisher, s3, env):
        super().__init__(router)

        # TODO: move some of these to the superclass if used more frequently
        self.storage_handler = storage_handler
        self.log = log
        self.publisher = publisher
        self.s3 = s3
        self.env = env

        self.router.add_api_route(
            "/file", self.create_upload_file, methods=["POST"], tags=["file"]
        )
        self.router.add_api_route(
            "/file/{file_uuid}",
            self.get_file,
            methods=["GET"],
            response_model=File,
            tags=["file"],
        )
        self.router.add_api_route(
            "/file/{file_uuid}",
            self.delete_file,
            methods=["DELETE"],
            response_model=File,
            tags=["file"],
        )
        self.router.add_api_route(
            "/file/{file_uuid}/chunks", self.get_file_chunks, tags=["file"]
        )
        self.router.add_api_route(
            "/file/{file_uuid}/status", self.get_file_status, tags=["file"]
        )

    async def create_upload_file(
        self, name: str, type: str, location: AnyHttpUrl
    ) -> UUID:
        """Upload a file to the object store and create a record in the database

        Args:
            name (str): The file name to be recorded
            type (str): The file type to be recorded
            location (AnyHttpUrl): The presigned file resource location

        Returns:
            UUID: The file uuid from the elastic database
        """

        file = File(
            name=name,
            url=str(location),  # avoids JSON serialisation error
            content_type=type,
        )

        self.storage_handler.write_item(file)

        self.log.info(f"publishing {file.uuid}")
        await self.publisher.publish(file)

        return file.uuid

    def get_file(self, file_uuid: UUID) -> File:
        """Get a file from the object store

        Args:
            file_uuid (str): The UUID of the file to get

        Returns:
            File: The file
        """
        return self.storage_handler.read_item(file_uuid, model_type="File")

    def delete_file(self, file_uuid: UUID) -> File:
        """Delete a file from the object store and the database

        Args:
            file_uuid (str): The UUID of the file to delete

        Returns:
            File: The file that was deleted
        """
        file = self.storage_handler.read_item(file_uuid, model_type="File")
        self.s3.delete_object(Bucket=self.env.bucket_name, Key=file.name)
        self.storage_handler.delete_item(file)

        chunks = self.storage_handler.get_file_chunks(file.uuid)
        self.storage_handler.delete_items(chunks)
        return file

    def get_file_chunks(self, file_uuid: UUID) -> list[Chunk]:
        self.log.info(f"getting chunks for file {file_uuid}")
        return self.storage_handler.get_file_chunks(file_uuid)

    def get_file_status(self, file_uuid: UUID) -> FileStatus:
        """Get the status of a file

        Args:
            file_uuid (str): The UUID of the file to get the status of

        Returns:
            File: The file with the updated status
        """
        try:
            status = self.storage_handler.get_file_status(file_uuid)
        except ValueError:
            raise HTTPException(status_code=404, detail=f"File {file_uuid} not found")

        return status
