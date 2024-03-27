import json
from datetime import date, datetime

import pydantic
import streamlit as st
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from streamlit_feedback import streamlit_feedback
from utils import StreamlitStreamHandler, init_session_state, load_llm_handler, replace_doc_ref, submit_feedback, get_persona_description

from redbox.llm.prompts.core import CORE_REDBOX_PROMPT
from redbox.models.chat import ChatMessage

st.set_page_config(page_title="Redbox Copilot - Ask the Box", page_icon="📮", layout="wide")

ENV = init_session_state()

# Model selector


def change_selected_model():
    load_llm_handler(ENV, update=True)
    st.write(st.session_state.llm)

persona_name = st.sidebar.selectbox(
    "What is your role?",
    options=st.session_state.available_personas,
    key="persona_select",
)

description = get_persona_description(persona_name)
st.sidebar.write(description)

user_info = st.session_state.user_info

INITIAL_CHAT_PROMPT = [
    ChatMessage(
        chain=None,
        message=SystemMessage(
            content=CORE_REDBOX_PROMPT.format(
                current_date=date.today().isoformat(),
                user_info=user_info,
            )
        ),
        creator_user_uuid=st.session_state.user_uuid,
    ),
    ChatMessage(
        chain=None,
        message=AIMessage(content="Hi, I'm Redbox Copilot. How can I help you?"),
        creator_user_uuid=st.session_state.user_uuid,
    ),
]


feedback_kwargs = {
    "feedback_type": "thumbs",
    "optional_text_label": "What did you think of this response?",
    "on_submit": submit_feedback,
}


clear_chat = st.sidebar.button("Clear Chat")

if "messages" not in st.session_state or clear_chat:
    st.session_state["messages"] = INITIAL_CHAT_PROMPT
    # clear feedback
    for key in list(st.session_state.keys()):
        if key.startswith("feedback_"):
            del st.session_state[key]
if "ai_message_markdown_lookup" not in st.session_state:
    st.session_state["ai_message_markdown_lookup"] = {}


def get_files_by_uuid(file_uuids):
    files = st.session_state.storage_handler.read_items(file_uuids, "File")
    return files


def render_citation_response(response):
    cited_chunks = [
        (
            chunk.metadata["parent_doc_uuid"],
            chunk.metadata["url"],
            (chunk.metadata["page_numbers"] if "page_numbers" in chunk.metadata else None),
        )
        for chunk in response["input_documents"]
    ]
    cited_chunks = set(cited_chunks)
    cited_files = get_files_by_uuid([x[0] for x in cited_chunks])
    page_numbers = [x[2] for x in cited_chunks]

    for j, page_number in enumerate(page_numbers):
        if isinstance(page_number, str):
            page_numbers[j] = json.loads(page_number)

    response_markdown = replace_doc_ref(
        str(response["output_text"]),
        cited_files,
        page_numbers=page_numbers,
        flexible=True,
    )

    return response_markdown


now_formatted = datetime.now().isoformat().replace(".", "_")

st.sidebar.download_button(
    label="Download Conversation",
    data=json.dumps(
        [x.message.dict() for x in st.session_state.messages],
        indent=4,
        ensure_ascii=False,
    ),
    file_name=(f"redboxai_conversation_{st.session_state.user_uuid}" f"_{now_formatted}.json"),
)

message_count = len(st.session_state.messages)

for i, chat_response in enumerate(st.session_state.messages):
    msg = chat_response.message
    if msg.type == "system":
        continue
    avatar_map = {"human": "🧑‍💻", "ai": "📮", "user": "🧑‍💻", "assistant": "📮"}
    if hash(msg.content) in st.session_state.ai_message_markdown_lookup:
        with st.chat_message(msg.type, avatar=avatar_map[msg.type]):
            st.markdown(
                st.session_state.ai_message_markdown_lookup[hash(msg.content)],
                unsafe_allow_html=True,
            )
    else:
        st.chat_message(msg.type, avatar=avatar_map[msg.type]).write(msg.content)

    if st.session_state.messages[i].message.type in ["ai", "assistant"] and i > 1:
        streamlit_feedback(
            **feedback_kwargs,
            key=f"feedback_{i}",
            kwargs={
                "input": [msg.message.content for msg in st.session_state.messages],
                "chain": st.session_state.messages[i].chain,
                "output": st.session_state.messages[i].message.content,
                "creator_user_uuid": st.session_state.user_uuid,
            },
        )


if prompt := st.chat_input():
    st.session_state.messages.append(
        ChatMessage(
            chain=None,
            message=HumanMessage(content=prompt),
            creator_user_uuid=st.session_state.user_uuid,
        )
    )
    st.chat_message("user", avatar=avatar_map["user"]).write(prompt)

    with st.chat_message("assistant", avatar=avatar_map["assistant"]):
        response_stream_text = st.empty()

        response, chain = st.session_state.llm_handler.chat_with_rag(
            user_question=prompt,
            user_info=st.session_state.user_info,
            chat_history=st.session_state.messages,
            callbacks=[
                StreamlitStreamHandler(text_element=response_stream_text, initial_text=""),
                st.session_state.llm_logger_callback,
            ],
        )

        response_final_markdown = render_citation_response(response)

        response_stream_text.empty()
        response_stream_text.markdown(response_final_markdown, unsafe_allow_html=True)

    st.session_state.messages.append(
        ChatMessage(
            chain=chain,
            message=AIMessage(content=response["output_text"]),
            creator_user_uuid=st.session_state.user_uuid,
        )
    )

    streamlit_feedback(
        **feedback_kwargs,
        key=f"feedback_{len(st.session_state.messages) - 1}",
        kwargs={
            "input": [msg.message.content for msg in st.session_state.messages],
            "chain": chain,
            "output": st.session_state.messages[-1].message.content,
            "creator_user_uuid": st.session_state.user_uuid,
        },
    )

    # Store the markdown response for later rendering
    # Done to avoid needing file references from llm_handler
    st.session_state.ai_message_markdown_lookup[hash(response["output_text"])] = response_final_markdown
