import logging
from typing import Optional
from uuid import UUID

from elastic_transport import ObjectApiResponse
from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.helpers import scan
from pydantic import ValidationError

from redbox.models import Chunk, ChunkStatus, FileStatus, ProcessingStatusEnum
from redbox.models.base import PersistableModel
from redbox.storage.storage_handler import BaseStorageHandler


class ElasticsearchStorageHandler(BaseStorageHandler):
    """Storage Handler for Elasticsearch"""

    def __init__(
        self,
        es_client: Elasticsearch,
        root_index: str = "redbox",
    ):
        """Initialise the storage handler

        Args:
            es_client (Elasticsearch): Elasticsearch client
            root_index (str, optional): Root index to use. Defaults to "redbox".
        """
        self.es_client = es_client
        self.root_index = root_index

    def refresh(self, index: str = "*") -> ObjectApiResponse:
        return self.es_client.indices.refresh(index=f"{self.root_index}-{index}")

    def write_item(self, item: PersistableModel) -> ObjectApiResponse:
        target_index = f"{self.root_index}-{item.model_type.lower()}"

        resp = self.es_client.index(
            index=target_index,
            id=str(item.uuid),
            body=item.json(),
        )
        return resp

    def write_items(self, items: list[PersistableModel]) -> list[ObjectApiResponse]:
        return list(map(self.write_item, items))

    def read_item(self, item_uuid: UUID, model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        result = self.es_client.get(index=target_index, id=str(item_uuid))
        model = self.get_model_by_model_type(model_type)
        item = model(**result.body["_source"])
        return item

    def read_items(self, item_uuids: list[UUID], model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        result = self.es_client.mget(index=target_index, body={"ids": list(map(str, item_uuids))})

        model = self.get_model_by_model_type(model_type)
        items = [model(**item["_source"]) for item in result.body["docs"]]

        return items

    def update_item(self, item: PersistableModel) -> ObjectApiResponse:
        target_index = f"{self.root_index}-{item.model_type.lower()}"

        resp = self.es_client.index(
            index=target_index,
            id=str(item.uuid),
            body=item.json(),
        )
        return resp

    def update_items(self, items: list[PersistableModel]) -> list[ObjectApiResponse]:
        return list(map(self.update_item, items))

    def delete_item(self, item: PersistableModel) -> ObjectApiResponse:
        target_index = f"{self.root_index}-{item.model_type.lower()}"
        result = self.es_client.delete(index=target_index, id=str(item.uuid))
        return result

    def delete_items(self, items: list[PersistableModel]) -> Optional[ObjectApiResponse]:
        if not items:
            return None

        model_type = items[0].model_type
        assert all(item.model_type == model_type for item in items)
        target_index = f"{self.root_index}-{model_type.lower()}"
        result = self.es_client.delete_by_query(
            index=target_index,
            body={"query": {"terms": {"_id": [str(item.uuid) for item in items]}}},
        )
        return result

    def read_all_items(self, model_type: str, user_uuid: UUID) -> list[PersistableModel]:
        target_index = f"{self.root_index}-{model_type.lower()}"
        try:
            result = scan(
                client=self.es_client,
                index=target_index,
                query={"query": {"match": {"creator_user_uuid": str(user_uuid)}}},
                _source=True,
            )

        except NotFoundError:
            print(f"Index {target_index} not found. Returning empty list.")
            return []

        # Grab the model we'll use to deserialize the items
        model = self.get_model_by_model_type(model_type)
        try:
            results = list(result)
        except NotFoundError:
            return []

        items = []
        for item in results:
            try:
                items.append(model(**item["_source"]))
            except ValidationError as e:
                logging.error(e)
        return items

    def list_all_items(self, model_type: str, user_uuid: UUID) -> list[UUID]:
        target_index = f"{self.root_index}-{model_type.lower()}"
        try:
            # Only return _id
            results = scan(
                client=self.es_client,
                index=target_index,
                query={"query": {"match": {"creator_user_uuid": str(user_uuid)}}},
                _source=False,
            )

        except NotFoundError:
            print(f"Index {target_index} not found. Returning empty list.")
            return []
        uuids = [UUID(item["_id"]) for item in results]
        return uuids

    def get_file_chunks(self, parent_file_uuid: UUID) -> list[Chunk]:
        """get chunks for a given file"""
        target_index = f"{self.root_index}-chunk"

        res = [
            Chunk(**item["_source"])
            for item in scan(
                client=self.es_client,
                index=target_index,
                query={"query": {"match": {"parent_file_uuid": str(parent_file_uuid)}}},
            )
        ]
        return res

    def _get_child_chunks(self, parent_file_uuid: UUID) -> list[UUID]:
        target_index = f"{self.root_index}-chunk"

        try:
            matched_chunk_ids = [
                UUID(x["_id"])
                for x in scan(
                    client=self.es_client,
                    index=target_index,
                    query={"query": {"match": {"parent_file_uuid": str(parent_file_uuid)}}},
                    _source=False,
                )
            ]
        except NotFoundError:
            print(f"Index {target_index} not found. Returning empty list.")
            return []

        return matched_chunk_ids

    def _get_embedded_child_chunks(self, parent_file_uuid: UUID) -> list[UUID]:
        target_index = f"{self.root_index}-chunk"
        matched_embedded_chunk_ids = [
            UUID(x["_id"])
            for x in scan(
                client=self.es_client,
                index=target_index,
                query={
                    "query": {
                        "bool": {
                            "must": [
                                {"match": {"parent_file_uuid": str(parent_file_uuid)}},
                                {"exists": {"field": "embedding"}},
                            ]
                        }
                    }
                },
                _source=False,
            )
        ]

        return matched_embedded_chunk_ids

    def get_file_status(self, file_uuid: UUID) -> FileStatus:
        """Get the status of a file and associated Chunks

        Args:
            file_uuid (UUID): The UUID of the file to get the status of

        Returns:
            FileStatus: The status of the file
        """

        # Test 1: Get the file
        try:
            self.read_item(file_uuid, "File")
        except NotFoundError:
            raise ValueError(f"File {file_uuid} not found")

        # Test 2: Get the number of chunks for the file
        chunk_uuids = self._get_child_chunks(file_uuid)

        if len(chunk_uuids) == 0:
            # File has not been chunked yet
            return FileStatus(
                file_uuid=file_uuid,
                chunk_statuses=[],
                processing_status=ProcessingStatusEnum.chunking,
            )

        # Test 3: Get the number of embedded chunks for the file
        embedded_chunk_uuids = self._get_embedded_child_chunks(file_uuid)

        chunk_statuses = [
            ChunkStatus(chunk_uuid=chunk_uuid, embedded=chunk_uuid in embedded_chunk_uuids)
            for chunk_uuid in chunk_uuids
        ]

        # Test 4: Determine the latest status
        if len(chunk_uuids) == len(embedded_chunk_uuids):
            latest_status = ProcessingStatusEnum.complete
        elif len(embedded_chunk_uuids) < len(chunk_uuids):
            latest_status = ProcessingStatusEnum.embedding
        else:
            raise ValueError("The number of embedded chunks should never exceed the number of chunks")

        return FileStatus(
            file_uuid=file_uuid,
            chunk_statuses=chunk_statuses,
            processing_status=latest_status,
        )
