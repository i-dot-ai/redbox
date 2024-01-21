import os
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field


class Collection(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    date: str = Field()
    name: str = Field()
    details: Optional[str] = Field(
        default="",
    )
    category: Optional[str] = Field(default="")
    deadline: Optional[str] = Field(default="")
    actions: Optional[str] = Field(default="")
    comment_ps: Optional[str] = Field(
        default=""
    )
    comment_principal: Optional[str] = Field(
        default=""
    )
    done: bool = Field(default=False)
    files: List[str] = Field(
        default=[]
    )

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

    def write_as_json(self, folder):
        with open(
            os.path.join(
                folder,
                self.date + " " + self.title + ".json",
            ),
            "w",
            encoding="UTF8",
        ) as f:
            f.write(self.model_dump_json(indent=4))

    def delete_json(self, folder):
        file_name = os.path.join(
            folder,
            self.date + " " + self.title + ".json",
        )
        if os.path.exists(file_name):
            os.remove(file_name)
        else:
            pass  # warning?
