import logging
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from elastic_transport import ObjectApiResponse
from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.helpers import scan
from pydantic import ValidationError

from redbox.models import Settings
from redbox.models.base import PersistableModel
from redbox.storage.storage_handler import BaseStorageHandler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def get_query_match_all_for_user(user_uuid: UUID):
    return {
        "query": {
            "bool": {
                "should": [
                    {"term": {"creator_user_uuid.keyword": str(user_uuid)}},
                    {"term": {"metadata.creator_user_uuid.keyword": str(user_uuid)}},
                ]
            }
        }
    }

class ElasticsearchStorageHandler(BaseStorageHandler):
    """Storage Handler for Elasticsearch"""

    def __init__(
        self,
        es_client: Elasticsearch,
        root_index: str,
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

        return self.es_client.index(
            index=target_index,
            id=str(item.uuid),
            body=item.model_dump(mode="json"),
        )

    def write_items(self, items: Sequence[PersistableModel]) -> Sequence[ObjectApiResponse]:
        return list(map(self.write_item, items))

    

    def read_item(self, item_uuid: UUID, model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        result = self.es_client.get(index=target_index, id=str(item_uuid))
        model = self.get_model_by_model_type(model_type)
        return model(**result.body["_source"])

    def read_items(self, item_uuids: list[UUID], model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        result = self.es_client.mget(index=target_index, body={"ids": list(map(str, item_uuids))})

        model = self.get_model_by_model_type(model_type)
        return [model(**item["_source"]) for item in result.body["docs"]]

    def update_item(self, item: PersistableModel) -> ObjectApiResponse:
        target_index = f"{self.root_index}-{item.model_type.lower()}"

        return self.es_client.index(
            index=target_index,
            id=str(item.uuid),
            body=item.model_dump(mode="json"),
        )

    def update_items(self, items: list[PersistableModel]) -> list[ObjectApiResponse]:
        return list(map(self.update_item, items))

    def delete_item(self, item: PersistableModel) -> ObjectApiResponse:
        target_index = f"{self.root_index}-{item.model_type.lower()}"
        return self.es_client.delete(index=target_index, id=str(item.uuid))

    def delete_items(self, items: list[PersistableModel]) -> ObjectApiResponse | None:
        if not items:
            return None

        if len({item.model_type for item in items}) > 1:
            message = "Items with differing model types: {item.model_type for item in items}"
            raise ValueError(message)
        model_type = items[0].model_type
        target_index = f"{self.root_index}-{model_type.lower()}"
        return self.es_client.delete_by_query(
            index=target_index,
            body={"query": {"terms": {"_id": [str(item.uuid) for item in items]}}},
        )
    
    def delete_user_items(self, model_type: str, user_uuid: UUID) -> ObjectApiResponse | None:
        target_index = f"{self.root_index}-{model_type.lower()}"
        return self.es_client.delete_by_query(
            index=target_index,
            body=get_query_match_all_for_user(user_uuid),
        )

    def read_all_items(self, model_type: str, user_uuid: UUID) -> list[PersistableModel]:
        target_index = f"{self.root_index}-{model_type.lower()}"
        try:
            result = scan(
                client=self.es_client,
                index=target_index,
                query=get_query_match_all_for_user(user_uuid),
                _source=True,
            )

        except NotFoundError:
            log.info("Index %s not found. Returning empty list.", target_index)
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
                log.exception("Validation exception for %s", item, exc_info=e)
        return items

    def list_all_items(self, model_type: str, user_uuid: UUID) -> list[UUID]:
        target_index = f"{self.root_index}-{model_type.lower()}"
        try:
            # Only return _id
            results = scan(
                client=self.es_client,
                index=target_index,
                query=get_query_match_all_for_user(user_uuid),
                _source=False,
            )

        except NotFoundError:
            log.info("Index %s not found. Returning empty list.", target_index)
            return []
        return [UUID(item["_id"]) for item in results]