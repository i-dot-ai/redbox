import datetime
import os
import uuid
from io import BytesIO

import streamlit as st
from streamlit_feedback import streamlit_feedback

from redbox.export.docx import spotlight_complete_to_docx
from redbox.models.spotlight import SpotlightComplete, SpotlightTaskComplete
from streamlit_app.utils import (
    StreamlitStreamHandler,
    hash_list_of_files,
    init_session_state,
    load_llm_handler,
    replace_doc_ref,
    submit_feedback,
)

# region ===== PAGE SETUP =====

st.set_page_config(
    page_title="Redbox Copilot - Summarise Documents",
    page_icon="📮",
    layout="wide",
)

st.title("Summarise Documents")

with st.spinner("Loading..."):
    ENV = init_session_state()

# Model selector


def change_selected_model():
    load_llm_handler(ENV, update=True)
    st.write(st.session_state.llm)


model_select = st.sidebar.selectbox(
    "Select Model",
    options=st.session_state.available_models,
    on_change=change_selected_model,
    key="model_select",
)


MAX_TOKENS = 100_000
if "current_token_count" not in st.session_state:
    st.session_state.current_token_count = 0

token_budget_ratio = float(st.session_state.current_token_count) / MAX_TOKENS
token_budget_tracker = st.sidebar.progress(
    value=(token_budget_ratio if token_budget_ratio <= 1 else 1),
)
token_budget_desc = st.sidebar.caption(
    body=f"Word Budget: {st.session_state.current_token_count}/{MAX_TOKENS}"
)


def on_summary_of_summaries_mode_change():
    st.session_state.summary_of_summaries_mode = not (
        st.session_state.summary_of_summaries_mode
    )
    if st.session_state.summary_of_summaries_mode:
        st.sidebar.info("Will summarise each document individually and combine them.")
    unsubmit_session_state()


summary_of_summaries_mode = st.sidebar.toggle(
    "Summary of Summaries",
    value=st.session_state.summary_of_summaries_mode,
    on_change=on_summary_of_summaries_mode_change,
)

feedback_kwargs = {
    "feedback_type": "thumbs",
    "optional_text_label": "What did you think of this response?",
    "on_submit": submit_feedback,
}


# endregion

spotlight_file_select = st.empty()


def update_token_budget_tracker():
    current_token_count = 0

    for selected_file_uuid in st.session_state.selected_files:
        selected_file = parsed_files_uuid_map[selected_file_uuid]
        current_token_count += selected_file.token_count

    if current_token_count > MAX_TOKENS:
        if not st.session_state.summary_of_summaries_mode:
            st.session_state.summary_of_summaries_mode = True
            st.toast(
                "Summary of Summaries mode enabled due to token budget",
                icon="⚠️",
            )

    st.session_state.current_token_count = current_token_count


def clear_params():
    st.query_params.clear()
    unsubmit_session_state()


def unsubmit_session_state():
    update_token_budget_tracker()
    st.session_state.spotlight = []
    st.session_state.submitted = False


if "submitted" not in st.session_state:
    st.session_state.submitted = False


# region ===== URL PARAM INJECTION =====
url_params = st.query_params.to_dict()


collections = st.session_state.storage_handler.read_all_items("Collection")
collections_by_uuid_map = {x.uuid: x for x in collections}
collection = None


parsed_files = st.session_state.storage_handler.read_all_items("File")
parsed_files_uuid_map = {x.uuid: x for x in parsed_files}

collection_select = st.selectbox(
    label="Collections",
    options=collections_by_uuid_map.keys(),
    index=None,
    format_func=lambda x: collections_by_uuid_map[x].name,
)

if collection_select is not None:
    url_params["collection_title"] = [collection_select]

if "collection_title" in url_params:
    collection_title = url_params["collection_title"][0]
    collection = st.session_state.storage_handler.read_item(
        item_uuid=collection_title, model_type="Collection"
    )

    files_from_url = [uuid.UUID(x) for x in collection.files]
    files_from_url = [x for x in files_from_url if x in parsed_files_uuid_map.keys()]

    spotlight_file_select = st.multiselect(
        label="Files",
        options=parsed_files_uuid_map.keys(),
        default=files_from_url,
        on_change=clear_params,
        format_func=lambda x: parsed_files_uuid_map[x].name,
        key="selected_files",
    )
    update_token_budget_tracker()
else:
    spotlight_file_select = st.multiselect(
        label="Files",
        options=parsed_files_uuid_map.keys(),
        default=[],
        on_change=unsubmit_session_state,
        format_func=lambda x: parsed_files_uuid_map[x].name,
        key="selected_files",
    )
    update_token_budget_tracker()
# endregion

submitted = st.button("Redbox Copilot Summary")

# Using this state trick to allow post gen download without reload.
if submitted:
    if spotlight_file_select:
        st.session_state.submitted = True
    else:
        st.warning("Please select document(s)")
        unsubmit_session_state()


files = []
for file in spotlight_file_select:
    files.append(parsed_files_uuid_map[file])

if len(files) == 0:
    st.stop()
SELECTED_FILE_HASH = hash_list_of_files(files)

spotlight_completed = st.session_state.storage_handler.read_all_items(
    model_type="SpotlightComplete"
)
spotlight_completed_by_hash = {x.file_hash: x for x in spotlight_completed}


# RENDER SPOTLIGHT
if st.session_state.submitted:
    if SELECTED_FILE_HASH in spotlight_completed_by_hash:
        st.info("Loading cached summary")
        cached_complete = spotlight_completed_by_hash[SELECTED_FILE_HASH]
        st.session_state.spotlight = cached_complete.tasks

    for completed_task in st.session_state.spotlight:
        st.subheader(completed_task.title, divider=True)
        st.markdown(completed_task.processed, unsafe_allow_html=True)
        streamlit_feedback(
            **feedback_kwargs,
            key=f"feedback_{completed_task.id}",
            kwargs={
                "input": [f.to_document().page_content for f in files],
                "chain": completed_task.chain,
                "output": completed_task.raw,
                "creator_user_uuid": st.session_state.user_uuid,
            },
        )

    if SELECTED_FILE_HASH not in spotlight_completed_by_hash:
        # RUN SPOTLIGHT
        spotlight_model = st.session_state.llm_handler.get_spotlight_tasks(
            files=files, file_hash=SELECTED_FILE_HASH
        )
        finished_tasks = [t.id for t in st.session_state.spotlight]
        for task in spotlight_model.tasks:
            if task.id not in finished_tasks:
                response_stream_header = st.subheader(task.title, divider=True)
                with st.status(
                    f"Generating {task.title}",
                    expanded=not st.session_state.summary_of_summaries_mode,
                    state="running",
                ):
                    response_stream_text = st.empty()
                    with response_stream_text:
                        (
                            response,
                            chain,
                        ) = st.session_state.llm_handler.run_spotlight_task(
                            spotlight=spotlight_model,
                            task=task,
                            user_info=st.session_state.user_info,
                            callbacks=[
                                StreamlitStreamHandler(
                                    text_element=response_stream_text,
                                    initial_text="",
                                ),
                                st.session_state.llm_logger_callback,
                            ],
                            map_reduce=st.session_state.summary_of_summaries_mode,
                        )
                        response_final_markdown = replace_doc_ref(response, files)

                        response_stream_header.empty()
                        response_stream_text.empty()

                complete = SpotlightTaskComplete(
                    id=task.id,
                    title=task.title,
                    chain=chain,
                    file_hash=spotlight_model.file_hash,
                    raw=response,
                    processed=response_final_markdown,
                    creator_user_uuid=st.session_state.user_uuid,
                )
                st.session_state.spotlight.append(complete)
                st.rerun()

        spotlight_complete = SpotlightComplete(
            file_hash=spotlight_model.file_hash,
            file_uuids=[str(f.uuid) for f in files],
            tasks=st.session_state.spotlight,
            creator_user_uuid=st.session_state.user_uuid,
        )

        st.session_state.storage_handler.write_item(item=spotlight_complete)
        spotlight_completed_by_hash[SELECTED_FILE_HASH] = spotlight_complete

    def spotlight_to_markdown():
        out = ""
        for completed_task in st.session_state.spotlight:
            out += "## " + completed_task.title + "\n\n"
            out += completed_task.processed + "\n\n"
        out += "---------------------------------------------------\n"
        out += "This summary is AI Generated and may be inaccurate."
        return out

    def spotlight_to_docx():
        if collection is not None:
            document = spotlight_complete_to_docx(
                spotlight_complete=spotlight_completed_by_hash[SELECTED_FILE_HASH],
                files=files,
                title=collection.name,
            )
        elif len(files) == 1:
            sanitised_file_name = files[0].name.replace("_", " ").replace("-", " ")
            # remove file extension
            sanitised_file_name = sanitised_file_name[: sanitised_file_name.rfind(".")]
            sanitised_file_name = sanitised_file_name.strip()

            # replace any multiple spaces with single space
            sanitised_file_name = " ".join(sanitised_file_name.split())

            document = spotlight_complete_to_docx(
                spotlight_complete=spotlight_completed_by_hash[SELECTED_FILE_HASH],
                files=files,
                title=sanitised_file_name,
            )
        else:
            document = spotlight_complete_to_docx(
                spotlight_complete=spotlight_completed_by_hash[SELECTED_FILE_HASH],
                files=files,
            )
        bytes_document = BytesIO()
        document.save(bytes_document)
        bytes_document.seek(0)
        return bytes_document

    if collection is not None:
        summary_file_name_root = (
            f"{collection.name}_{datetime.datetime.now().isoformat()}_summary"
        )
    else:
        summary_file_name_root = f"{datetime.datetime.now().isoformat()}_summary"

    st.sidebar.download_button(
        label="Download DOCX",
        data=spotlight_to_docx(),
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_name=f"{summary_file_name_root}.docx",
    )

    st.sidebar.download_button(
        label="Download TXT",
        data=spotlight_to_markdown(),
        mime="text/plain",
        file_name=f"{summary_file_name_root}.txt",
    )

    def delete_summary():
        spotlight_completed_to_delete = spotlight_completed_by_hash[SELECTED_FILE_HASH]
        st.session_state.storage_handler.delete_item(
            item_uuid=spotlight_completed_to_delete.uuid, model_type="SpotlightComplete"
        )
        del spotlight_completed_by_hash[SELECTED_FILE_HASH]

        st.session_state.spotlight = []
        st.session_state.submitted = False
        st.query_params.clear()

    delete_summary = st.sidebar.button(
        label="Delete Summary",
        on_click=delete_summary,
    )
