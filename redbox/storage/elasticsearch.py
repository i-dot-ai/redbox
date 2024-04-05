from uuid import UUID

from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.helpers import scan

from redbox.models import Chunk, FileStatus
from redbox.models.base import PersistableModel
from redbox.models.file import ProcessingStatusEnum
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

    def write_item(self, item: PersistableModel):
        target_index = f"{self.root_index}-{item.model_type.lower()}"

        resp = self.es_client.index(
            index=target_index,
            id=str(item.uuid),
            body=item.json(),
        )
        return resp

    def write_items(self, items: list[PersistableModel]):
        responses = []
        for item in items:
            resp = self.write_item(item)
            responses.append(resp)
        return responses

    def read_item(self, item_uuid: UUID, model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        result = self.es_client.get(index=target_index, id=str(item_uuid))
        model = self.get_model_by_model_type(model_type)
        item = model(**result.body["_source"])
        return item

    def read_items(self, item_uuids: list[UUID], model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        result = self.es_client.mget(
            index=target_index, body={"ids": list(map(str, item_uuids))}
        )

        model = self.get_model_by_model_type(model_type)
        items = [model(**item["_source"]) for item in result.body["docs"]]

        return items

    def update_item(self, item_uuid: UUID, item: PersistableModel):
        target_index = f"{self.root_index}-{item.model_type.lower()}"

        self.es_client.index(
            index=target_index,
            id=str(item.uuid),
            body=item.json(),
        )

    def update_items(self, item_uuids: list[UUID], items: list[PersistableModel]):
        for item_uuid, item in zip(item_uuids, items):
            self.update_item(item_uuid, item)

    def delete_item(self, item_uuid: UUID, model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        result = self.es_client.delete(index=target_index, id=str(item_uuid))
        return result

    def delete_items(self, item_uuids: list[UUID], model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        result = self.es_client.delete_by_query(
            index=target_index,
            body={"query": {"terms": {"_id": list(map(str, item_uuids))}}},
        )
        return result

    def read_all_items(self, model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        try:
            result = scan(
                client=self.es_client,
                index=target_index,
                query={"query": {"match_all": {}}},
                _source=True,
            )

            # Unpack from scrolling generator
            results = [item for item in result]

        except NotFoundError:
            print(f"Index {target_index} not found. Returning empty list.")
            return []

        # Grab the model we'll use to deserialize the items
        model = self.get_model_by_model_type(model_type)
        items = [model(**item["_source"]) for item in results]
        return items

    def list_all_items(self, model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        try:
            # Only return _id
            result = scan(
                client=self.es_client,
                index=target_index,
                query={"query": {"match_all": {}}},
                _source=False,
            )

            # Unpack from scrolling generator
            results = [item for item in result]

        except NotFoundError:
            print(f"Index {target_index} not found. Returning empty list.")
            return []
        uuids = [item["_id"] for item in results]
        return uuids

    def get_file_chunks(self, parent_file_uuid: UUID) -> list[Chunk]:
        """get chunks for a given file"""
        target_index = f"{self.root_index}-chunk"

        res = [
            item["_source"]
            for item in scan(
                client=self.es_client,
                index=target_index,
                query={"query": {"match": {"parent_file_uuid": str(parent_file_uuid)}}},
            )
        ]
        return res

    def _count_chunks(self, parent_file_uuid: UUID) -> int:
        target_index = f"{self.root_index}-chunk"
        res = self.es_client.count(
            index=target_index,
            body={"query": {"match": {"parent_file_uuid": str(parent_file_uuid)}}},
        )
        return res["count"]

    def _count_embedded_chunks(self, parent_file_uuid: UUID) -> int:
        target_index = f"{self.root_index}-chunk"
        res = self.es_client.count(
            index=target_index,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"parent_file_uuid": str(parent_file_uuid)}},
                            {"exists": {"field": "embedding"}},
                        ]
                    }
                }
            },
        )
        return res["count"]

    def get_file_status(self, file_uuid: UUID) -> FileStatus:
        file = self.read_item(file_uuid, model_type="File")
        if file.processing_status == "embedding":
            chunk_count = self._count_chunks(file_uuid)
            embedded_chunk_count = self._count_embedded_chunks(file_uuid)

            if chunk_count == embedded_chunk_count:
                file.processing_status = ProcessingStatusEnum.complete
                self.update_item(file_uuid, file)

        status = FileStatus(
            uuid=file.uuid,
            processing_status=file.processing_status,
        )
        return status
