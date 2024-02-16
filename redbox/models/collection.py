from typing import List

from pydantic import Field, computed_field

from redbox.models.base import PersistableModel


class Collection(PersistableModel):
    name: str = Field()
    files: List[str] = Field(default=[])

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__

    def remove_file(self, file_name: str):
        self.files = [x for x in self.files if x != file_name]

    def add_file(self, one_file: str):
        if one_file not in self.files:
            self.files.append(one_file)
