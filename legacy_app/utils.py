import base64
import hashlib
import os
import pathlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union

import boto3
import cognitojwt
import dotenv
import html2markdown
import pandas as pd
import streamlit as st
from elasticsearch import Elasticsearch
from langchain.callbacks import FileCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains.base import Chain
from langchain.schema.output import LLMResult
from langchain.vectorstores.elasticsearch import (
    ApproxRetrievalStrategy,
    ElasticsearchStore,
)
from langchain_community.chat_models import ChatAnthropic
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.llms import Bedrock
from loguru import logger
from lxml.html.clean import Cleaner
from pyprojroot import here
from streamlit.web.server.websocket_headers import _get_websocket_headers

from redbox.llm.llm_base import LLMHandler
from redbox.models.feedback import Feedback
from redbox.models.file import File
from redbox.storage import ElasticsearchStorageHandler, FileSystemStorageHandler


def get_user_name(principal: dict) -> str:
    """Get the user name from the principal object

    Args:
        principal (dict): the principal object

    Returns:
        str: the user name

    """
    for obj in principal["claims"]:
        if obj["typ"] == "name":
            return obj["val"]
    return ""


def populate_user_info(ENV: dict) -> dict:
    """Populate the user information in the sidebar

    Args:
        ENV (dict): the environment variables dictionary

    Returns:
        dict: the user information dictionary
    """
    headers = _get_websocket_headers()

    if headers is not None:
        if "X-Amzn-Oidc-Accesstoken" in headers:
            try:
                jwt_dict = cognitojwt.decode(
                    token=headers["X-Amzn-Oidc-Accesstoken"],
                    region=ENV["COGNITO_REGION"],
                    userpool_id=ENV["COGNITO_USERPOOL_ID"],
                    app_client_id=ENV["COGNITO_APP_CLIENT_ID"],
                )
                user_details = {"username": jwt_dict["username"]}
            except TypeError:
                st.error("Error decoding JWT from Cognito")
                st.write(headers)
                st.stop()

            user_details["username_md5"] = hashlib.md5(
                user_details["username"].encode("utf-8")
            ).hexdigest()
            return user_details
        else:
            st.sidebar.markdown("Running Locally")
            return {"name": "dev", "email": "dev@example.com"}


def init_session_state() -> dict:
    """
    Initialise the session state and return the environment variables

    Returns:
        dict: the environment variables dictionary
    """
    # Bring VARS into environment from any .env file
    DOT_ENV = dotenv.dotenv_values(".env")
    # Grab it as a dictionary too for convenience
    ENV = dict(os.environ)
    # Update the environment with the .env file
    if DOT_ENV:
        ENV.update(DOT_ENV)

    st.markdown(
        """
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
    </style>
    """,
        unsafe_allow_html=True,
    )

    if "user_details" not in st.session_state:
        st.session_state["user_details"] = populate_user_info(ENV)

    if "user_uuid" not in st.session_state:
        if ENV["DEV_MODE"] == "true":
            st.session_state.user_uuid = "dev"
        else:
            if "username_md5" not in st.session_state.user_details:
                st.session_state.user_uuid = "local"
            else:
                # MD5 of the username is used as the user_uuid
                st.session_state.user_uuid = st.session_state.user_details[
                    "username_md5"
                ]

    if "BUCKET_NAME" not in st.session_state:
        st.session_state.BUCKET_NAME = f"redbox-storage-{st.session_state.user_uuid}"

    if "s3_client" not in st.session_state:
        if ENV["OBJECT_STORE"] == "minio":
            st.session_state.s3_client = boto3.client(
                "s3",
                endpoint_url=f"http://{ENV['MINIO_HOST']}:9000",
                aws_access_key_id=ENV["MINIO_ACCESS_KEY"],
                aws_secret_access_key=ENV["MINIO_SECRET_KEY"],
            )
        elif ENV["OBJECT_STORE"] == "s3":
            raise NotImplementedError("S3 not yet implemented")

    if "storage_handler" not in st.session_state:
        if ENV["STORAGE_MODE"] == "filesystem":
            persistency_folder_path = pathlib.Path(
                os.path.join(here(), "data", str(st.session_state.user_uuid))
            )
            st.session_state.storage_handler = FileSystemStorageHandler(
                root_path=persistency_folder_path
            )
        elif ENV["STORAGE_MODE"] == "elasticsearch":
            es = Elasticsearch(
                hosts=[
                    {
                        "host": "elasticsearch",
                        "port": 9200,
                        "scheme": "http",
                    }
                ],
                basic_auth=(ENV["ELASTIC_USER"], ENV["ELASTIC_PASSWORD"]),
            )
            st.session_state.storage_handler = ElasticsearchStorageHandler(
                es_client=es, root_index="redbox-data"
            )

    if st.session_state.user_uuid == "dev":
        st.sidebar.info("**DEV MODE**")
        with st.sidebar.expander("⚙️ DEV Settings", expanded=False):
            model_params = {
                "max_tokens": st.number_input(
                    label="max_tokens",
                    min_value=0,
                    max_value=100_000,
                    value=4096,
                    step=1,
                ),
                "temperature": st.slider(
                    label="temperature",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.2,
                    step=0.01,
                ),
            }
            reload_llm = st.button(label="♻️ Reload LLM and LLMHandler")
            if reload_llm:
                load_llm_handler(ENV=ENV, model_params=model_params)

            if st.button(label="Empty Streamlit Cache"):
                st.cache_data.clear()

            if st.button(label="Empty LLM Prompt Cache"):
                st.session_state.llm_handler.clear_cache()

    else:
        model_params = {"max_tokens": 4096, "temperature": 0.2}

    if "llm" not in st.session_state or "llm_handler" not in st.session_state:
        load_llm_handler(ENV=ENV, model_params=model_params)

    # check we have all expected data folders

    if "llm_logger_callback" not in st.session_state:
        logfile = os.path.join(
            "llm_logs",
            f"llm_{datetime.now().isoformat(timespec='seconds')}.log",
        )
        logger.add(logfile, colorize=True, enqueue=True)
        st.session_state.llm_logger_callback = FileCallbackHandler(logfile)

    if "user_info" not in st.session_state:
        st.session_state.user_info = {
            "name": "",
            "email": "",
            "department": "Cabinet Office",
            "role": "Civil Servant",
            "preffered_language": "British English",
        }

    if "spotlight" not in st.session_state:
        st.session_state.spotlight = []

    if "summary_of_summaries_mode" not in st.session_state:
        st.session_state.summary_of_summaries_mode = False

    return ENV


def get_link_html(
    page: str, text: str, query_dict: dict = None, target: str = "_self"
) -> str:
    """Returns a link in HTML format

    Args:
        page (str): the page to link to
        text (str): the text to display
        query_dict (dict, optional): query parameters. Defaults to None.
        target (str, optional): the target of the link. Defaults to "_self".

    Returns:
        str: _description_
    """
    if query_dict is not None:
        query = "&".join(f"{k}={v}" for k, v in query_dict.items())
        query = "?" + query
    else:
        query = ""

    return f"<a href='/{page}{query}' target={target}><button style='background-color: white;border-radius: 8px;'>{text}</button></a>"


def get_file_link(file: File, page: int = None) -> str:
    """Returns a link to a file

    Args:
        file (File): the file to link to
        page (int, optional): the page to link to in the file. Defaults to None.

    Returns:
        _type_: _description_
    """
    # we need to refer to files by their uuid instead
    if len(file.name) > 45:
        presentation_name = file.name[:45] + "..."
    else:
        presentation_name = file.name
    query_dict = {"file_uuid": file.uuid}
    if page is not None:
        query_dict["page_number"] = page[0]

    link_html = get_link_html(
        page="Preview_Files",
        query_dict=query_dict,
        text=presentation_name,
    )

    return link_html


def get_bedrock_client(ENV):
    """Returns a bedrock client

    Args:
        ENV (_type_): the environment variables dictionary

    Returns:
        _type_:
    """
    bedrock_client = boto3.client("bedrock-runtime", region_name=ENV["REGION"])
    return bedrock_client


def load_llm_handler(ENV, model_params) -> None:
    """Loads the LLM and LLMHandler into the session state

    Args:
        ENV (_type_): the environment variables dictionary
        model_params (_type_): the model parameters

    """

    if "llm" not in st.session_state:
        if "BEDROCK_MODEL_ID" in ENV:
            if ENV["BEDROCK_MODEL_ID"] != "" or ENV["BEDROCK_MODEL_ID"] is not None:
                bedrock_client = get_bedrock_client(ENV)

                st.session_state.llm = Bedrock(
                    model_id=ENV["BEDROCK_MODEL_ID"],
                    model_kwargs={
                        "max_tokens_to_sample": model_params["max_tokens"],
                        "temperature": model_params["temperature"],
                    },
                    client=bedrock_client,
                    streaming=True,
                )
        else:
            st.session_state.llm = ChatAnthropic(
                anthropic_api_key=ENV["ANTHROPIC_API_KEY"],
                max_tokens=model_params["max_tokens"],
                temperature=model_params["temperature"],
                streaming=True,
            )

    if "llm_handler" not in st.session_state:
        if ENV["STORAGE_MODE"] == "filesystem":
            st.session_state.llm_handler = LLMHandler(
                llm=st.session_state.llm, user_uuid=st.session_state.user_uuid
            )
        elif ENV["STORAGE_MODE"] == "elasticsearch":
            embedding_function = SentenceTransformerEmbeddings()

            vector_store = ElasticsearchStore(
                es_url=f"http://{ENV['ELASTIC_HOST']}:9200",
                es_user=ENV["ELASTIC_USER"],
                es_password=ENV["ELASTIC_PASSWORD"],
                index_name="redbox-vector",
                embedding=embedding_function,
                strategy=ApproxRetrievalStrategy(hybrid=True),
            )

            st.session_state.llm_handler = LLMHandler(
                llm=st.session_state.llm,
                user_uuid=st.session_state.user_uuid,
                vector_store=vector_store,
            )


def hash_list_of_files(list_of_files: List[File]) -> str:
    """Returns a hash of the list of files

    Args:
        list_of_files (List[File]): the list of files

    Returns:
        str: the hash of the list of files
    """
    hash_list = [file.text_hash for file in list_of_files]
    return hashlib.sha256("".join(sorted(hash_list)).encode("utf-8")).hexdigest()


class StreamlitStreamHandler(BaseCallbackHandler):
    """Callback handler for rendering LLM output to streamlit UI"""

    def __init__(self, text_element, initial_text=""):
        self.text_element = text_element
        self.text = initial_text

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Callback for new token from LLM and append to text"""
        self.text += token
        self.text_element.write(self.text)

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Callback for end of LLM generation to empty text"""
        self.text_element.empty()

    def sync(self):
        """Syncs the text element with the text"""
        self.text_element.write(self.text)


class FilePreview(object):
    """Class for rendering files to streamlit UI"""

    def __init__(self):
        self.cleaner = Cleaner()
        self.cleaner.javascript = True

        self.render_methods = {
            ".pdf": self._render_pdf,
            ".txt": self._render_txt,
            ".xlsx": self._render_xlsx,
            ".csv": self._render_csv,
            ".eml": self._render_eml,
            ".html": self._render_html,
            ".docx": self._render_docx,
        }

    def st_render(self, file: File) -> None:
        """Outputs the given file to streamlit UI

        Args:
            file (File): The file to preview
        """

        render_method = self.render_methods[file.type]
        render_method(file)

    def _render_pdf(self, file: File, page_number: int = None) -> None:
        with open(file.path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode("utf-8")
            if page_number is not None:
                iframe = f"""<iframe
                            title="{file.name}" \
                            src="data:application/pdf;base64,{base64_pdf}#page={page_number}" \
                            width="100%" \
                            height="1000" \
                            type="application/pdf"></iframe>"""
            else:
                iframe = f"""<iframe
                            title="{file.name}" \
                            src="data:application/pdf;base64,{base64_pdf}" \
                            width="100%" \
                            height="1000" \
                            type="application/pdf"></iframe>"""

            st.markdown(iframe, unsafe_allow_html=True)

    def _render_txt(self, file: File) -> None:
        with open(file.path, "r", encoding="utf-8") as f:
            st.markdown(f"{f.read()}", unsafe_allow_html=True)

    def _render_xlsx(self, file: File) -> None:
        df = pd.read_excel(file.path)
        st.dataframe(df, use_container_width=True)

    def _render_csv(self, file: File) -> None:
        df = pd.read_csv(file.path)
        st.dataframe(df, use_container_width=True)

    def _render_eml(self, file: File) -> None:
        # TODO Visual Formatting could be improved.
        with open(file.path, "r", encoding="utf-8") as f:
            st.markdown(self.cleaner.clean_html(f.read()), unsafe_allow_html=True)

    def _render_html(self, file: File) -> None:
        with open(file.path, "r", encoding="utf-8") as f:
            markdown_html = html2markdown.convert(f.read())
            st.markdown(markdown_html, unsafe_allow_html=True)

    def _render_docx(self, file: File) -> None:
        st.warning("DOCX preview not yet supported.")
        with open(file.path, "rb") as f:
            st.download_button(
                label=file.name,
                data=f.read(),
                mime="application/msword",
                file_name=file.name,
            )


def replace_doc_ref(
    output_for_render: str = "",
    files: List[File] = [],
    page_numbers: List = [],
    flexible=False,
) -> str:
    """Replaces references to files in the output text with links to the files

    Args:
        output_for_render (str, optional): The text to modify. Defaults to "".
        files (List[File], optional): The files to link to. Defaults to [].
        page_numbers (List, optional): Any page numbers to link to within files. Defaults to [].
        flexible (bool, optional): Whether to replace edgecase references with or without spaces. Defaults to False.

    Returns:
        str: The modified text
    """
    if len(page_numbers) != len(files):
        page_numbers = [None for _ in files]

    modified_text = output_for_render

    for i, file in enumerate(files):
        page = page_numbers[i]
        file_link = get_file_link(file=file, page=page)

        strings_to_replace = [
            f"<Doc{file.uuid}>",
        ]
        if flexible:
            # For when the LLM returns a space between Doc and the uuid
            strings_to_replace += [
                f"<Doc {file.uuid}>",
                f"Doc {file.uuid}",
                f"Document {file.uuid}",
            ]

        for string_to_replace in strings_to_replace:
            modified_text = modified_text.replace(string_to_replace, file_link)
    return modified_text


def eval_csv_to_squad_json(csv_path: str, json_path: str) -> None:
    """Converts a csv file with columns 'question', 'answer', 'document' to a json file in SQuAD format.

    Args:
        csv_path (str): The path to the csv file
        json_path (str): The path to the json file
    """
    df = pd.read_csv(csv_path)
    df["uuid"] = df.apply(lambda _: uuid.uuid4(), axis=1)
    (
        df.rename(dict(answer="ground_truth_answer", document="document_name"), axis=1)
        .set_index("uuid")
        .to_json(orient="index", indent=4, path_or_buf=json_path)
    )


def submit_feedback(
    feedback: Dict,
    input: Union[str, List[str]],
    output: str,
    creator_user_uuid: str,
    chain: Optional[Chain] = None,
) -> None:
    """Submits feedback to the storage handler

    Args:
        feedback (Dict): A dictionary containing the feedback
        input (Union[str, List[str]]): Input text from the user
        output (str): The output text from the LLM
        creator_user_uuid (str): The uuid of the user who created the feedback
        chain (Optional[Chain], optional): The chain used to generate the output. Defaults to None.
    """
    to_write = Feedback(
        input=input,
        chain=chain,
        output=output,
        feedback_type=feedback["type"],
        feedback_score=feedback["score"],
        feedback_text=feedback["text"],
        creator_user_uuid=creator_user_uuid,
    )
    st.session_state.storage_handler.write_item(to_write)

    st.toast("Thanks for your feedback!", icon="🙏")
