import json
import logging
import os
import pathlib
from typing import List, Any

from pydantic import BaseModel, TypeAdapter
from pyprojroot import here

from redbox.models import Chunk, Collection, Feedback, File, SpotlightComplete, TagGroup
from redbox.storage.storage_handler import BaseStorageHandler

logger = logging.Logger(__file__)

default_root_path = here() / "data"

models_to_store = [
    Chunk,
    Collection,
    Feedback,
    File,
    SpotlightComplete,
    TagGroup,
]


class FileSystemStorageHandler(BaseStorageHandler):
    def __init__(self, root_path: pathlib.Path = default_root_path):
        self.root_path = root_path

        # Initialise directories in root path for each model

        for model in models_to_store:
            model_path = self.root_path / model.__name__
            if not os.path.exists(model_path):
                os.makedirs(model_path)

        self.upload_folder = self.root_path / "Upload"

        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)

    def write_item(self, item: type[BaseModel]):
        """Write an object to a data store"""
        with open(
            self.root_path / item.__class__.__name__ / f"{item.uuid}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(item.model_dump(), f, indent=4, ensure_ascii=False)

    def write_items(self, items: list):
        """Write a list of objects to a data store"""
        for item in items:
            self.write_item(item)

    def read_item(self, item_uuid: str, model_type: str) -> Any:
        """Read an object from a data store"""
        with open(
            self.root_path / model_type / f"{item_uuid}.json", "r", encoding="utf-8"
        ) as f:
            item_dict = json.load(f)
            model = self.get_model_by_model_type(model_type)
            item = TypeAdapter(model).validate_python(item_dict)
            return item

    def read_items(self, item_uuids: List[str], model_type: str) -> list[Any]:
        """Read a list of objects from a data store"""
        items = []
        for item_uuid in item_uuids:
            try:
                items.append(self.read_item(item_uuid, model_type))
            except FileNotFoundError:
                logger.warning(
                    f"file not found {self.root_path}/{model_type}/{item_uuid}.json"
                )
        return items

    def update_item(self, item_uuid: str, item: type[BaseModel]):
        """Update an object in a data store"""
        self.write_item(item)

    def update_items(self, item_uuids: List[str], items: List[type[BaseModel]]):
        """Update a list of objects in a data store"""
        for item in items:
            self.write_item(item)

    def delete_item(self, item_uuid: str, model_type: str):
        """Delete an object from a data store"""
        os.remove(self.root_path / model_type / f"{item_uuid}.json")

    def delete_items(self, item_uuids: List[str], model_type: str):
        """Delete a list of objects from a data store"""
        for item_uuid in item_uuids:
            self.delete_item(item_uuid, model_type)

    def list_all_items(self, model_type: str) -> list[str]:
        """List all objects of a given type from a data store"""
        raw_file_names = os.listdir(self.root_path / model_type)
        item_uuids = [x.split(".")[0] for x in raw_file_names]
        return item_uuids

    def read_all_items(self, model_type: str) -> list[Any]:
        """Read all objects of a given type from a data store"""
        raw_file_names = os.listdir(self.root_path / model_type)
        item_uuids = [x.split(".")[0] for x in raw_file_names]
        return self.read_items(item_uuids, model_type)
