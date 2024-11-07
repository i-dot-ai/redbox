from datetime import datetime
from typing import Type, Optional

import requests
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, tool

from langchain_community.utilities import WikipediaAPIWrapper, ArxivAPIWrapper

from langchain_community.tools import WikipediaQueryRun, ArxivQueryRun
from pydantic import BaseModel, Field


class GovUKQueryInput(BaseModel):
    """Input for the GovUKQuery tool."""

    query: str = Field(description="query to look up on gov.uk")


class GovUKQueryRun(BaseTool):
    """Tool that searches the Wikipedia API."""

    name: str = "gov-uk"
    description: str = """
    Search for documents on gov.uk based on a query string.
    This endpoint is used to search for documents on gov.uk. There are many types of documents on gov.uk.
    Types include:
    - guidance
    - policy
    - legislation
    - news
    - travel advice
    - departmental reports
    - statistics
    - consultations
    - appeals
    """

    args_schema: Type[BaseModel] = GovUKQueryInput
    url_base: str = "https://www.gov.uk"
    num_results: int = 10
    required_fields: list[str] = ["format", "title", "description", "indexable_content", "link"]

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the GOV.UK tool."""

        response = requests.get(
            f"{self.url_base}/api/search.json",
            params={
                "q": query,
                "count": self.num_results,
                "fields": self.required_fields,
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        response = response.json()

        documents = []
        for i, doc in enumerate(response["results"]):
            documents.append("\n\n".join(f"{field}: {doc.get(field)}" for field in self.required_fields))

        return "\n\n".join(documents)


@tool("talking-clock")
def taking_clock():
    """tells the time"""
    return datetime.now()


wiki_api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=300)
wiki_tool = WikipediaQueryRun(api_wrapper=wiki_api_wrapper)

arxiv_api_wrapper = ArxivAPIWrapper(top_k_results=1, doc_content_chars_max=300)
arxiv_tool = ArxivQueryRun(api_wrapper=arxiv_api_wrapper)
govuk_tool = GovUKQueryRun()
