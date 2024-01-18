from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel

from redbox.models import Chunk, Collection, Feedback, File, SpotlightComplete, TagGroup


class BaseStorageHandler(ABC):
    """Abstract Class for Storage Handler which manages all file and object IO
    the Redbox backend.

    Args:
        ABC (_type_): _description_
    """

    # dict comprehension for lowercase class name to class
    model_type_map = {
        v.__name__.lower(): v
        for v in [Chunk, Collection, Feedback, File, SpotlightComplete, TagGroup]
    }

    def get_model_by_model_type(self, model_type):
        return self.model_type_map[model_type.lower()]

    @abstractmethod
    def __init__(self):
        """Initialise the storage handler"""
        pass

    @abstractmethod
    def write_item(self, item: type[BaseModel]):
        """Write an object to a data store"""
        pass

    @abstractmethod
    def write_items(self, items: list):
        """Write a list of objects to a data store"""
        pass

    @abstractmethod
    def read_item(self, item_uuid: str, model_type: str):
        """Read an object from a data store"""
        pass

    @abstractmethod
    def read_items(self, item_uuids: List[str], model_type: str):
        """Read a list of objects from a data store"""
        pass

    @abstractmethod
    def update_item(self, item_uuid: str, item: type[BaseModel]):
        """Update an object in a data store"""
        pass

    @abstractmethod
    def update_items(self, item_uuids: List[str], items: List[type[BaseModel]]):
        """Update a list of objects in a data store"""
        pass

    @abstractmethod
    def delete_item(self, item_uuid: str, model_type: str):
        """Delete an object from a data store"""
        pass

    @abstractmethod
    def delete_items(self, item_uuids: List[str], model_type: str):
        """Delete a list of objects from a data store"""
        pass

    @abstractmethod
    def list_all_items(self, model_type: str):
        """List all objects of a given type from a data store"""
        pass

    @abstractmethod
    def read_all_items(self, model_type: str):
        """Read all objects of a given type from a data store"""
        pass
