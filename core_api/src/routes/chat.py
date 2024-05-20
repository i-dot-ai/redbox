import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, WebSocket
from fastapi.responses import HTMLResponse
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.llm import LLMChain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_community.chat_models import ChatLiteLLM
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_elasticsearch import ApproxRetrievalStrategy, ElasticsearchStore

from core_api.src.auth import get_user_uuid
from redbox.llm.prompts.chat import (
    CONDENSE_QUESTION_PROMPT,
    STUFF_DOCUMENT_PROMPT,
    WITH_SOURCES_PROMPT,
)
from redbox.model_db import MODEL_PATH
from redbox.models import EmbeddingModelInfo, Settings
from redbox.models.chat import ChatMessage, ChatRequest, ChatResponse, SourceDocument

# === Logging ===

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


chat_app = FastAPI(
    title="Core Chat API",
    description="Redbox Core Chat API",
    version="0.1.0",
    openapi_tags=[
        {"name": "chat", "description": "Chat interactions with LLM and RAG backend"},
        {"name": "embedding", "description": "Embedding interactions with SentenceTransformer"},
        {"name": "llm", "description": "LLM information and parameters"},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

log.info("Loading embedding model from environment: %s", env.embedding_model)
embedding_model = SentenceTransformerEmbeddings(model_name=env.embedding_model, cache_folder=MODEL_PATH)
log.info("Loaded embedding model from environment: %s", env.embedding_model)


def populate_embedding_model_info() -> EmbeddingModelInfo:
    test_text = "This is a test sentence."
    embedding = embedding_model.embed_documents([test_text])[0]
    embedding_model_info = EmbeddingModelInfo(
        embedding_model=env.embedding_model,
        vector_size=len(embedding),
    )
    return embedding_model_info


embedding_model_info = populate_embedding_model_info()


# === LLM setup ===


llm = ChatLiteLLM(
    model="gpt-3.5-turbo",
    streaming=True,
)

es = env.elasticsearch_client()
if env.elastic.subscription_level == "basic":
    strategy = ApproxRetrievalStrategy(hybrid=False)
elif env.elastic.subscription_level in ["platinum", "enterprise"]:
    strategy = ApproxRetrievalStrategy(hybrid=True)
else:
    raise ValueError(f"Unknown Elastic subscription level {env.elastic.subscription_level}")


vector_store = ElasticsearchStore(
    es_connection=es,
    index_name="redbox-data-chunk",
    embedding=embedding_model,
    strategy=strategy,
    vector_query_field="embedding",
)


@chat_app.post("/vanilla", tags=["chat"], response_model=ChatResponse)
def simple_chat(chat_request: ChatRequest, _user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> ChatResponse:
    """Get a LLM response to a question history"""

    if len(chat_request.message_history) < 2:
        raise HTTPException(
            status_code=422,
            detail="Chat history should include both system and user prompts",
        )

    if chat_request.message_history[0].role != "system":
        raise HTTPException(
            status_code=422,
            detail="The first entry in the chat history should be a system prompt",
        )

    if chat_request.message_history[-1].role != "user":
        raise HTTPException(
            status_code=422,
            detail="The final entry in the chat history should be a user question",
        )

    chat_prompt = ChatPromptTemplate.from_messages((msg.role, msg.text) for msg in chat_request.message_history)
    # Convert to LangChain style messages
    messages = chat_prompt.format_messages()

    response = llm(messages)

    return ChatResponse(response_message=ChatMessage(text=response.text, role="ai"))


@chat_app.post("/rag", tags=["chat"])
def rag_chat(chat_request: ChatRequest, user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> ChatResponse:
    """Get a LLM response to a question history and file

    Args:


    Returns:
        StreamingResponse: a stream of the chain response
    """
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

    standalone_question = condense_question_chain({"question": question, "chat_history": previous_history})["text"]

    docs = vector_store.as_retriever(
        search_kwargs={"filter": {"term": {"creator_user_uuid.keyword": str(user_uuid)}}}
    ).get_relevant_documents(standalone_question)

    result = docs_with_sources_chain(
        {
            "question": standalone_question,
            "input_documents": docs,
        },
    )

    source_documents = [
        SourceDocument(
            page_content=langchain_document.page_content,
            file_uuid=langchain_document.metadata.get("parent_doc_uuid"),
            page_numbers=langchain_document.metadata.get("page_numbers"),
        )
        for langchain_document in result.get("input_documents", [])
    ]
    return ChatResponse(output_text=result["output_text"], source_documents=source_documents)


@chat_app.websocket("/rag-stream-old")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    retrieval_chain = await build_retrieval_chain()

    while True:
        chat_request = ChatRequest.parse_raw(await websocket.receive_text())
        chat_history = [
            HumanMessage(content=x.text) if x.role == "user" else AIMessage(content=x.text)
            for x in chat_request.message_history[:-1]
        ]
        chat = {"chat_history": chat_history, "input": chat_request.message_history[-1].text}

        async for event in retrieval_chain.astream_events(chat, version="v1"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                message = json.dumps({"resource_type": "text", "data": event["data"]["chunk"].content})
                await websocket.send_text(message)
            if kind == "on_chat_model_end":
                message = json.dumps({"resource_type": "end"})
                await websocket.send_text(message)
            elif kind == "on_retriever_end":
                source_documents = [
                    SourceDocument(
                        page_content=document.page_content,
                        file_uuid=document.metadata.get("parent_doc_uuid"),
                        page_numbers=document.metadata.get("page_numbers"),
                    )
                    for document in event["data"]["output"]["documents"]
                ]
                message = json.dumps({"resource_type": "documents", "data": source_documents})
                await websocket.send_text(message)


@chat_app.websocket("/rag-chat-stream")
async def rag_chat_streamed(websocket: WebSocket):
    await websocket.accept()

    retrieval_chain = await build_retrieval_chain()

    chat_request = ChatRequest.parse_raw(await websocket.receive_text())
    chat_history = [
        HumanMessage(content=x.text) if x.role == "user" else AIMessage(content=x.text)
        for x in chat_request.message_history[:-1]
    ]
    chat = {"chat_history": chat_history, "input": chat_request.message_history[-1].text}
    async for event in retrieval_chain.astream_events(chat, version="v1"):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            message = json.dumps({"resource_type": "text", "data": event["data"]["chunk"].content})
            await websocket.send_text(message)
        if kind == "on_chat_model_end":
            message = json.dumps({"resource_type": "end"})
            await websocket.send_text(message)

    await websocket.close()


async def build_retrieval_chain():
    prompt_search_query = ChatPromptTemplate.from_messages(
        [
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            (
                "user",
                "Given the above conversation, generate a search query to look up to get information relevant to the "
                "conversation",
            ),
        ]
    )
    retriever_chain = create_history_aware_retriever(llm, vector_store.as_retriever(), prompt_search_query)
    prompt_get_answer = ChatPromptTemplate.from_messages(
        [
            ("system", "Answer the user's questions based on the below context:\\n\\n{context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
        ]
    )
    document_chain = create_stuff_documents_chain(llm, prompt_get_answer)
    return create_retrieval_chain(retriever_chain, document_chain)


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
        <script>
            var ws = new WebSocket("ws://localhost:5002/chat/rag-stream");

            // Change binary type from "blob" to "arraybuffer"
            ws.binaryType = "arraybuffer";

            var decoder = new TextDecoder("utf-8");

            // Listen for messages
            ws.addEventListener("message", (event) => {
              if (event.data instanceof ArrayBuffer) {
                document.getElementById('documents').innerHTML =
                  JSON.stringify(JSON.parse(decoder.decode(event.data)),null,2);
              } else {
                var li = document.getElementById("messages").getElementsByTagName("li");
                li[li.length-1].innerHTML += event.data;
              }
            });

            function sendMessage(event) {
                message_history = [];

                var question = document.getElementById('messageText');
                var messages = document.getElementById("messages");
                var li = document.createElement("li");
                li.innerText = question.value;
                messages.appendChild(li);
                var input = messages.getElementsByTagName("li");

                for (var i = 0; i < input.length; i++ ) {
                    var role = i % 2 == 0? "user": "ai";
                    message_history.push({"text": input[i].innerText, "role": role});
                }
                ws.send(JSON.stringify({"message_history": message_history}));

                question.value = '';
                messages.appendChild(document.createElement("li"));
                event.preventDefault();
            }
        </script>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <div id='messages'>
            <li>who is the prime minister</li>
            <li>Rishi Sunak MP</li>
        </div>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" placeholder="Enter your next question"  autocomplete="off"/>
            <button>Send</button>
        </form>
        <pre id='documents'>
        </pre>
    </body>
</html>
"""


@chat_app.get("/chit-chat")
async def get():
    return HTMLResponse(html)
