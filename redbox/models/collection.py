from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field


class Collection(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field()
    files: List[str] = Field(default=[])
    created_datetime: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    creator_user_uuid: Optional[str]

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__

    def remove_file(self, file_name: str):
        self.files = [x for x in self.files if x != file_name]

    def add_file(self, one_file: str):
        if one_file not in self.files:
            self.files.append(one_file)
