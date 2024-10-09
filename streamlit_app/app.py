import streamlit as st
from redbox.app import Redbox
from redbox.models.chain import RedboxQuery, RedboxState, AISettings
from uuid import uuid4
from redbox.models.settings import Settings
from dotenv import load_dotenv
import asyncio

load_dotenv("../.env")



def run_streamlit():
    chat_tab, settings_tab = st.tabs(["chat", "settings"])
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "ai_settings" not in st.session_state:
        st.session_state.ai_settings = AISettings()
    if "redbox" not in st.session_state:
        st.session_state.redbox = Redbox(env=Settings(), debug=True)

    with chat_tab:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["text"])

        if prompt := st.chat_input("What is up?"):
            st.session_state.messages.append({"role":"user", "text":prompt})
            state = RedboxState(
                request=RedboxQuery(
                    question=prompt,
                    s3_keys=[],
                    user_uuid=uuid4(),
                    chat_history=[],
                    ai_settings=st.session_state.ai_settings
                ),
            )
            response: RedboxState = asyncio.run(st.session_state.redbox.run(state))
            llm_answer = response["text"]
            route = response["route_name"]
            with st.chat_message("ai"):
                st.write(llm_answer)
            st.session_state.messages.append({"role":"ai", "text":llm_answer})
            
            
run_streamlit()

# getting the chat history to work, showing the routes, and sources, and getting it to look like Redbox. 
# Go back to James re-files, data and streaming