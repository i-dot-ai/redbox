import os
import string

import streamlit as st
from pyprojroot import here
from utils import init_session_state

from redbox.models.classification import Tag, TagGroup

st.set_page_config(page_title="Tag builder", page_icon="⚙️", layout="wide")

# Initialise session state variables

ENV = init_session_state()


user_prefs_folder = os.path.join(
    here(), "data", str(st.session_state.user_uuid), "user_preferences"
)


if "current_classes" not in st.session_state:
    st.session_state.current_classes = []
if "current_classes_files" not in st.session_state:
    st.session_state.current_classes_files = (
        st.session_state.storage_handler.read_all_items(model_type="File")
    )
if "current_classes_tags" not in st.session_state:
    st.session_state.current_classes_tags = {}


def alphabet_generator(alpha=string.ascii_uppercase):
    letters = list(alpha)
    n = 0
    while True:
        yield letters[n]
        n += 1
        if n == len(letters):
            n = 0


tag_letters = alphabet_generator()

# Page proper

if st.session_state.user_uuid == "dev":
    group_name = st.text_input("Classification group name")
    all_classes = st.empty()

    with st.form("add_tag"):
        tag = st.text_input("Add class")
        if st.form_submit_button("Add"):
            if tag not in st.session_state.current_classes:
                st.session_state.current_classes.append(tag)
            all_classes.multiselect(
                "Current document classes",
                options=st.session_state.current_classes,
                default=st.session_state.current_classes,
            )
            if all_classes != st.session_state.current_classes:
                if isinstance(all_classes, list):
                    st.session_state.current_classes = all_classes

    with st.form("Create classification group"):
        if len(st.session_state.current_classes) > 0:
            for tag in st.session_state.current_classes:
                letter = next(tag_letters)

                with st.expander(f"({letter}) {tag}", expanded=True):
                    file_uuid_map = {
                        x.uuid: x for x in st.session_state.current_classes_files
                    }
                    examples = st.multiselect(
                        f"Choose examples of {tag}",
                        options=file_uuid_map.keys(),
                        key=f"{letter}_examples",
                        format_func=lambda x: file_uuid_map[x].name,
                    )

                example_files = []
                for example in examples:
                    example_files.append(file_uuid_map[example])

                st.session_state.current_classes_tags[letter] = Tag(
                    letter=letter, description=tag, examples=example_files
                )

        if st.form_submit_button("Export classification group"):
            new_tag_group = TagGroup(
                name=group_name,
                tags=list(st.session_state.current_classes_tags.values()),
                creator_user_uuid=st.session_state.user_uuid,
            )
            st.session_state.storage_handler.write_item(new_tag_group)

            st.toast(f"Saved classifcation group '{new_tag_group.name}'")

else:
    st.write("This page is currently for dev mode only")
