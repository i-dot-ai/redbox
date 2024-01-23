import json
import os
import pathlib
from datetime import date

import streamlit as st
from pydantic import TypeAdapter
from pyprojroot import here
from utils import init_session_state

from redbox.models import Collection, File, TagGroup
from redbox.parsing.file_chunker import FileChunker

st.set_page_config(
    page_title="Redbox Copilot - Add Documents", page_icon="📮", layout="wide"
)

ENV = init_session_state()

file_chunker = FileChunker()

# Folder setup and loading

system_prefs_folder = os.path.join(here(), "legacy_app", "system_preferences")
default_taggroups = []
for default_taggroup_file in os.listdir(system_prefs_folder):
    with open(
        os.path.join(system_prefs_folder, default_taggroup_file), "r", encoding="utf-8"
    ) as f:
        default_taggroups.append(TypeAdapter(TagGroup).validate_python(json.load(f)))


taggroups = (
    st.session_state.storage_handler.read_all_items(model_type="TagGroup")
    + default_taggroups
)
collections = st.session_state.storage_handler.read_all_items(model_type="Collection")


# Upload form


uploaded_files = st.file_uploader(
    "Upload your documents",
    accept_multiple_files=True,
    type=file_chunker.supported_file_types,
)

new_collection_str = "➕ New collection..."
no_collection_str = " No associated collection"
collection_uuid_name_map = {x.uuid: x.name for x in collections}
collection_uuid_name_map[new_collection_str] = new_collection_str
collection_uuid_name_map[no_collection_str] = no_collection_str

collection_selection = st.selectbox(
    "Add to collection:",
    options=collection_uuid_name_map.keys(),
    index=list(collection_uuid_name_map.keys()).index(new_collection_str),
    format_func=lambda x: collection_uuid_name_map[x],
)

new_collection = st.text_input("New collection name:")


# Create text input for user entry for new collection

submitted = st.button("Upload to Redbox Copilot collection")

data_folder = os.path.join(here(), "data", str(st.session_state.user_uuid))

if submitted:  # noqa: C901
    if collection_selection == new_collection_str:
        if not new_collection:
            st.error("Please enter a collection name")
            st.stop()
        elif new_collection in collection_uuid_name_map.values():
            st.error("Collection name already exists")
            st.stop()

    # associate selected collection with the uploaded files
    if collection_selection == new_collection_str:
        collection_obj = Collection(
            date=date.today().isoformat(),
            name=new_collection,
            creator_user_uuid=st.session_state.user_uuid,
        )
    elif collection_selection == no_collection_str:
        collection_obj = Collection(
            date="", name="", creator_user_uuid=st.session_state.user_uuid
        )
    else:
        collection_obj = st.session_state.storage_handler.read_item(
            item_uuid=collection_selection, model_type="Collection"
        )

    for file_index, uploaded_file in enumerate(uploaded_files):
        # ==================== UPLOAD ====================
        with st.spinner(f"Uploading {uploaded_file.name}"):
            bytes_data = uploaded_file.getvalue()

            sanitised_name = uploaded_file.name
            sanitised_name = sanitised_name.replace("'", "_")

            file_type = pathlib.Path(sanitised_name).suffix

            st.session_state.s3_client.put_object(
                Bucket=ENV["BUCKET_NAME"],
                Body=bytes_data,
                Key=sanitised_name,
                Tagging=f"file_type={file_type}&user_uuid={st.session_state.user_uuid}",
            )

            file = File(
                path=sanitised_name,
                type=file_type,
                name=sanitised_name,
                storage_kind=ENV["OBJECT_STORE"],
                creator_user_uuid=st.session_state.user_uuid,
            )

            url = st.session_state.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": "filestore", "Key": "hello.txt"},
                ExpiresIn=3600,
            )

        # ==================== CHUNKING ====================

        with st.spinner(f"Chunking **{file.name}**"):
            try:
                chunks = file_chunker.chunk_file(
                    file=file, creator_user_uuid=st.session_state.user_uuid
                )
            except TypeError as err:
                st.error(f"Failed to chunk {file.name}, error: {str(err)}")
                st.write(file.model_dump())
                continue

        # ==================== CLASSIFICATION ====================

        with st.spinner(f"Classifying **{file.name}**"):
            # Saving combined text to File record too (useful for Summarise Documents)
            try:
                file_path = os.path.join(data_folder, "file", f"{file.name}.json")
                file.text = "".join([chunk.text for chunk in chunks])

                file_classifications = {}
                for taggroup in taggroups:
                    # Classify using the first N characters of the file
                    tag = st.session_state.llm_handler.classify_to_tag(
                        group=taggroup, raw_text=file.text[:1000]
                    )
                    file_classifications[taggroup.name] = tag.model_dump()
                file.classifications = file_classifications
            except Exception as e:
                st.error(f"Failed to classify {file.name}, error: {str(e)}")
                st.write(file.model_dump())
                st.write(taggroups)
                raise e
                # continue

        # ==================== SAVING ====================

        with st.spinner(f"Saving **{file.name}**"):
            try:
                st.session_state.storage_handler.write_item(item=file)
                st.session_state.storage_handler.write_items(items=chunks)
            except Exception as e:
                st.error(
                    f"Failed to save {file.name} and or its chunks, error: {str(e)}"
                )
                continue

        # ==================== INDEXING ====================

        with st.spinner(f"Indexing **{file.name}**"):
            try:
                st.session_state.llm_handler.add_chunks_to_vector_store(chunks=chunks)
            except Exception as e:
                st.error(f"Failed to index {file.name}, error: {str(e)}")
                st.write(len(chunks))
                st.write(chunks)
                continue

        st.toast(body=f"{file.name} Complete")

        collection_obj.files.append(file.uuid)

    if collection_obj.name and (collection_obj.name != "none"):
        st.session_state.storage_handler.write_item(item=collection_obj)
