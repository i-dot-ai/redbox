from typing import Optional
from uuid import UUID

from elastic_transport import ObjectApiResponse
from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.helpers import scan

from redbox.models import Chunk
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

    def read_all_items(self, model_type: str) -> list[PersistableModel]:
        target_index = f"{self.root_index}-{model_type.lower()}"
        try:
            results = scan(
                client=self.es_client,
                index=target_index,
                query={"query": {"match_all": {}}},
                _source=True,
            )

        except NotFoundError:
            print(f"Index {target_index} not found. Returning empty list.")
            return []

        # Grab the model we'll use to deserialize the items
        model = self.get_model_by_model_type(model_type)
        try:
            items = [model(**item["_source"]) for item in results]
            return items
        except NotFoundError:
            return []

    def list_all_items(self, model_type: str) -> list[UUID]:
        target_index = f"{self.root_index}-{model_type.lower()}"
        try:
            # Only return _id
            results = scan(
                client=self.es_client,
                index=target_index,
                query={"query": {"match_all": {}}},
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
