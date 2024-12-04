from pathlib import Path

import pandas as pd
import pytest
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from redbox.chains.components import get_chat_llm
from redbox.models.chain import AISettings
from redbox.models.settings import ChatLLMBackend

from .cases import AITestCase

# Test whether a gov.uk search should be called


@pytest.fixture
def template():
    return "You are an expert assistant. Given a user question, evaluate if you need to call gov search to get additional information. User question: {question}. Instruction:\n return answer if you do not need to call gov.uk search, otherwise return `QUERY:` followed by query that you will use at gov.uk search\n You must follow the instruction"


@pytest.fixture(
    params=[
        ChatLLMBackend(name="gpt-4o-2024-08-06", provider="azure-openai"),
        # ChatLLMBackend(=name="anthropic.claude-3-sonnet-20240229-v1:0", provider="bedrock"),
    ],
    ids=["default"],  # "claude"],
)
def ai_settings(request):
    return AISettings(chat_backend=request.param)


def create_chat_chain(ai_settings, template):
    chat = get_chat_llm(ai_settings.chat_backend)
    template = PromptTemplate(template=template, input_variables=["question"])
    return template | chat | StrOutputParser()


def save_response(prompts, response, output_dir):
    file_path = output_dir / "gov_search_eval.csv"
    df = pd.DataFrame()
    if Path.exists(file_path):
        df = pd.read_csv(file_path)
    pd.concat(
        [
            df,
            pd.DataFrame(
                {
                    "prompts": prompts,
                    "LLM response": response,
                    "Gov search call": "QUERY" in response,
                }
            ),
        ],
    ).to_csv(file_path, index=False)


def test_gov_search_eval(test_case: AITestCase, ai_settings, template, output_dir: Path = Path("data/output")):
    chain = create_chat_chain(ai_settings, template)
    response = chain.invoke({"question": test_case.prompts})
    save_response(test_case.prompts, response, output_dir)
