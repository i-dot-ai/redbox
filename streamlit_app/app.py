# Set up
import streamlit as st
from redbox.app import Redbox
from redbox.models.chain import RedboxQuery, RedboxState, AISettings
from redbox.models.settings import get_settings
from uuid import uuid4
from dotenv import load_dotenv
import asyncio

# Load Redbox environment variables
load_dotenv("../.env")


# Function defining how the Redbox streamlit app will work
def run_streamlit():
    # Create two tabs within the interface, one labeled "chat", the other labeled "settings"
    chat_tab, settings_tab = st.tabs(["chat", "settings"])
    # Create a list that will store the chat history, if one does not already exist
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # Create a list that will store the AI settings, if one does not already exist
    if "ai_settings" not in st.session_state:
        st.session_state.ai_settings = AISettings()
    # Create an instance of Redbox, if one does not already exist
    if "redbox" not in st.session_state:
        st.session_state.redbox = Redbox(env=get_settings(), debug=True)

    with chat_tab:
        # Iterate over the messages list, display each message in the chat window with the role and corresponding text
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["text"])
        # Present an input field where the user can type a message to Redbox
        if prompt := st.chat_input("How can I help you today?"):
            # New messages should be added to the chat history under the "user" role
            st.session_state.messages.append({"role": "user", "text": prompt})
            # Construct a Redbox object with required information
            state = RedboxState(
                request=RedboxQuery(
                    question=prompt,
                    s3_keys=[],
                    user_uuid=uuid4(),
                    chat_history=[],
                    ai_settings=st.session_state.ai_settings,
                ),
            )
            # Run an asynchronous function from the Redbox instance to get the AI's response
            response: RedboxState = asyncio.run(st.session_state.redbox.run(state))
            llm_answer = response["text"]
            # route = response["route_name"] - to be added back in if / when routing is added
            # Display the AI's response in the chat under the "ai" role and append it to the chat history
            with st.chat_message("ai"):
                st.write(llm_answer)
            st.session_state.messages.append({"role": "ai", "text": llm_answer})


run_streamlit()

# getting the chat history to work, showing the routes, and sources, and getting it to look like Redbox.
# Go back to James re-files, data and streaming
