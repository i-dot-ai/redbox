from pydantic import Field

from redbox.models.base import PersistableModel


class Collection(PersistableModel):
    name: str = Field()
    files: list[str] = Field(default_factory=list)

    def remove_file(self, file_name: str):
        self.files = [x for x in self.files if x != file_name]

    def add_file(self, one_file: str):
        if one_file not in self.files:
            self.files.append(one_file)
