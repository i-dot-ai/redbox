from operator import itemgetter

from langchain_core.runnables import Runnable, RunnableLambda
from langchain.schema import StrOutputParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.prompts import ChatPromptTemplate

from core_api.src.format import format_docs



def make_stuff_document_runnable(
    system_prompt: str,
    llm: ChatLiteLLM,
) -> Runnable:
    """Takes a system prompt and LLM returns a stuff document runnable.
    
    Runnable takes input of a dict keyed to question, messages and documents.
    """
    chat_history = [
        ("system", system_prompt),
        ("placeholder", "{messages}"),
        ("user", "Question: {question}. \n\n Documents: \n\n {documents} \n\n Answer: "),
    ]

    chain = (
        {
            "question": itemgetter("question"),
            "messages": itemgetter("messages"),
            "content": itemgetter("documents") | RunnableLambda(format_docs),
        }
        | ChatPromptTemplate.from_messages(chat_history)
        | llm
        | StrOutputParser()
    )

    return chain
