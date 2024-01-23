import streamlit as st
from utils import init_session_state

st.set_page_config(
    page_title="Redbox Copilot",
    page_icon="📮",
)

ENV = init_session_state()

st.write("# Redbox Copilot")


st.markdown(
    """\
    ### What can you do?
    * [Add Documents](/Add_Documents) by uploading them
    * [Summarise Documents](/Summarise_Documents) to extract key dates, people, actions and discussion for your principal
    * [Ask the Box](/Ask_the_Box) will answer questions about your box's content
"""
)
