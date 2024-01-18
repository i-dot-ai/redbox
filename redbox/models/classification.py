import re
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.prompts.prompt import PromptTemplate
from pydantic import BaseModel, Field, computed_field, create_model, field_validator

from redbox.models.file import File

DOC_CAT_EXAMPLE_TEMPLATE = PromptTemplate(
    input_variables=["document", "answer"],
    template="""\
        Document:
        <document>
        {document}
        </document>
        Assistant: My answer is {{{{"letter": "{answer}"}}}}\
    """,
)

DOC_CAT_PREFIX_TEMPLATE = """\
You are a customer service agent that is classifying documents. \
The document is wrapped in <document></document> XML tags.

Categories are:

{layer_list_items}\
"""

DOC_CAT_SUFFIX_TEMPLATE = """\

Here is the document, wrapped in <document></document> XML tags
<document>
{raw_text}
</document>

{format_instructions} \

Assistant: My answer is {{"letter": "\
"""


class Tag(BaseModel):
    letter: str
    description: str
    examples: Optional[List[File]] = None

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__

    @field_validator("letter")
    @classmethod
    def letter_to_upper(cls, v: str) -> str:
        return v.upper()

    @computed_field
    def var(self) -> str:
        alpha_regex = re.compile("[^a-zA-Z_]")
        space_to_score = self.description.replace(" ", "_").lower()
        return re.sub(alpha_regex, "", space_to_score)

    def get_examples(self):
        examples = []
        for example in self.examples:
            to_add = {"document": example.text, "answer": self.letter}
            examples.append(to_add)
        return examples

    def get_list_item(self):
        return f"({self.letter}) {self.description}"


class TagGroup(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    tags: List[Tag]
    default_tag_index: int = -1

    created_datetime: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    creator_user_uuid: Optional[str]

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__

    def get_examples(self):
        examples = []
        for tag in self.tags:
            if tag.examples is not None:
                examples += tag.get_examples()
        return examples

    def get_list_items(self):
        list_items = ""
        for tag in self.tags:
            list_items += tag.get_list_item() + " \n"
        return list_items

    def get_letters(self):
        return [tag.letter for tag in self.tags]

    def get_default_tag(self):
        return self.tags[self.default_tag_index]

    def make_validator(self):
        def letter_validator(cls, v):
            assert v in self.get_letters(), description
            return v

        description = (
            "Must be a single uppercase letter of the alphabet corresponding "
            "to one of the following: \n\n"
            f"{self.get_list_items()}"
        )

        validators = {"letter_validator": field_validator("letter")(letter_validator)}

        return create_model(self.name, letter=(str, ...), __validators__=validators)

    def get_tag(self, letter):
        validator = self.make_validator()
        validator(letter=letter)
        for tag in self.tags:
            if tag.letter == letter:
                return tag

    def get_parser(self):
        return PydanticOutputParser(pydantic_object=self.make_validator())

    def get_classification_prompt_template(self, parser=None):
        if parser is None:
            parser = self.get_parser()

        return FewShotPromptTemplate(
            examples=self.get_examples(),
            example_prompt=DOC_CAT_EXAMPLE_TEMPLATE,
            prefix=DOC_CAT_PREFIX_TEMPLATE,
            suffix=DOC_CAT_SUFFIX_TEMPLATE,
            input_variables=["raw_text"],
            partial_variables={
                "layer_list_items": self.get_list_items(),
                "format_instructions": parser.get_format_instructions(),
            },
        )
