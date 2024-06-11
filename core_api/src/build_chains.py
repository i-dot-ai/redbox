from os import system

from langchain.chains.llm import LLMChain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_elasticsearch import ElasticsearchStore

from core_api.src.runnables import (
    make_es_retriever,
    make_rag_runnable,
    make_stuff_document_runnable,
)

# Define the system prompt for summarization
summarisation_prompt = """
You are an AI assistant tasked with summarizing documents. Your goal is to extract the most important information and present it in a concise and coherent manner. Please follow these guidelines while summarizing:
1) Identify and highlight key points,
2) Avoid repetition,
3) Ensure the summary is easy to understand,
4) Maintain the original context and meaning.
"""


async def build_vanilla_chain(
    chat_request: ChatRequest,
) -> ChatPromptTemplate:
    """Get a LLM response to a question history"""

    if len(chat_request.message_history) < 2:  # noqa: PLR2004
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="Chat history should include both system and user prompts",
        )

    if chat_request.message_history[0].role != "system":
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="The first entry in the chat history should be a system prompt",
        )

    if chat_request.message_history[-1].role != "user":
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="The final entry in the chat history should be a user question",
        )

    return ChatPromptTemplate.from_messages(
        (msg.role, msg.text) for msg in chat_request.message_history
    )


async def build_retrieval_chain(
    chat_request: ChatRequest,
    user_uuid: UUID,
    llm: ChatLiteLLM,
    vector_store: ElasticsearchStore,
):
    question = chat_request.message_history[-1].text
    previous_history = list(chat_request.message_history[:-1])
    previous_history = ChatPromptTemplate.from_messages(
        (msg.role, msg.text) for msg in previous_history
    ).format_messages()

    docs_with_sources_chain = load_qa_with_sources_chain(
        llm,
        chain_type="stuff",
        prompt=WITH_SOURCES_PROMPT,
        document_prompt=STUFF_DOCUMENT_PROMPT,
        verbose=True,
    )

    condense_question_chain = LLMChain(llm=llm, prompt=CONDENSE_QUESTION_PROMPT)

    standalone_question = condense_question_chain(
        {"question": question, "chat_history": previous_history}
    )["text"]

    search_kwargs = {
        "filter": {
            "bool": {"must": [{"term": {"creator_user_uuid.keyword": str(user_uuid)}}]}
        }
    }

    if chat_request.selected_files is not None:
        search_kwargs["filter"]["bool"]["should"] = [
            {"term": {"parent_file_uuid.keyword": str(file.uuid)}}
            for file in chat_request.selected_files
        ]

    docs = vector_store.as_retriever(
        search_kwargs=search_kwargs
    ).get_relevant_documents(standalone_question)

    params = {
        "question": standalone_question,
        "input_documents": docs,
    }

    return docs_with_sources_chain, params


# (build_stuff_chain, make_stuff_document_runnable)


async def build_stuff_chain(
    chat_request: ChatRequest,
    user_uuid: UUID,
    llm: ChatLiteLLM,
    vector_store: ElasticsearchStore,
):
    question = chat_request.message_history[-1].text
    previous_history = list(chat_request.message_history[:-1])

    context = chat_request.selected_files

    chain = make_stuff_document_runnable(summarisation_prompt, llm)

    params = {
        "question": question,
        "content": context,
        "messages": [(msg.role, msg.text) for msg in previous_history],
    }

    return chain, params
