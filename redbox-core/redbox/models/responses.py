

from pydantic import BaseModel, Field


class Source(BaseModel):
    source: str = Field(description="URL or reference to the source")
    source_type: str = Field(description="creator_type of tool")
    document_name: str
    highlighted_text_in_source: str
    page_numbers: list[int] = Field(description="Page Number in document the highlighted text is on", default=[])


class Citation(BaseModel):
    text_in_answer: str = Field(
        description="Part of text from `answer` that references sources and matches exactly with the `answer`, without rephrasing or altering the meaning. Partial matches are acceptable as long as they are exact excerpts from the `answer`",
    )
    sources: list[Source] = Field(description="List of Sources which support the text in answer")


class StructuredResponseWithCitations(BaseModel):
    answer: str = Field(description="Answer to the query in markdown")
    citations: list[Citation] = Field(description="The answer must be supported by a list of Citations which reference the provided documents", default_factory=list)