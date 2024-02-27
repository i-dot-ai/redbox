from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.helpers import scan

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

    def write_item(self, item: PersistableModel):
        model_type = item.model_type.lower()  # type: ignore
        target_index = f"{self.root_index}-{model_type}"

        resp = self.es_client.index(
            index=target_index,
            id=item.uuid,
            body=item.model_dump(),
        )
        return resp

    def write_items(self, items: list):
        responses = []
        for item in items:
            resp = self.write_item(item)
            responses.append(resp)
        return responses

    def read_item(self, item_uuid: str, model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        result = self.es_client.get(index=target_index, id=item_uuid)
        model = self.get_model_by_model_type(model_type)
        item = model(**result.body["_source"])
        return item

    def read_items(self, item_uuids: list[str], model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        result = self.es_client.mget(index=target_index, body={"ids": item_uuids})

        model = self.get_model_by_model_type(model_type)
        items = [model(**item["_source"]) for item in result.body["docs"]]

        return items

    def update_item(self, item_uuid: str, item: PersistableModel):
        model_type = item.model_type.lower()  # type: ignore
        target_index = f"{self.root_index}-{model_type}"

        self.es_client.index(
            index=target_index,
            id=item.uuid,
            body=item.model_dump(),
        )

    def update_items(self, item_uuids: list[str], items: list[PersistableModel]):
        for item_uuid, item in zip(item_uuids, items):
            self.update_item(item_uuid, item)

    def delete_item(self, item_uuid: str, model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        result = self.es_client.delete(index=target_index, id=item_uuid)
        return result

    def delete_items(self, item_uuids: list[str], model_type: str):
        target_index = f"{self.root_index}-{model_type.lower()}"
        result = self.es_client.delete_by_query(
            index=target_index,
            body={"query": {"terms": {"_id": item_uuids}}},
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
