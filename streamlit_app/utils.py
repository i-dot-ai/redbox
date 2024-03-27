import base64
import hashlib
import os
import uuid
from datetime import datetime
from io import BytesIO
from typing import Optional

import boto3
import dotenv
import html2markdown
import pandas as pd
import streamlit as st
from botocore.client import ClientError
from elasticsearch import Elasticsearch
from langchain.callbacks import FileCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains.base import Chain
from langchain.schema.output import LLMResult
from langchain.vectorstores.elasticsearch import ApproxRetrievalStrategy, ElasticsearchStore
from langchain_community.chat_models import ChatLiteLLM
from langchain_community.embeddings import SentenceTransformerEmbeddings
from loguru import logger
from lxml.html.clean import Cleaner

from model_db import SentenceTransformerDB
from redbox.llm.llm_base import LLMHandler
from redbox.models.feedback import Feedback
from redbox.models.file import File
from redbox.models.persona import ChatPersona
from redbox.storage import ElasticsearchStorageHandler


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


def populate_user_info() -> dict:
    """Populate the user information

    Args:
        ENV (dict): the environment variables dictionary

    Returns:
        dict: the user information dictionary
    """
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
        st.session_state["user_details"] = populate_user_info()

    if "user_uuid" not in st.session_state:
        st.session_state.user_uuid = st.session_state["user_details"]["name"]

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

    if "available_models" not in st.session_state:
        st.session_state.available_models = []

        if "OPENAI_API_KEY" in ENV:
            if ENV["OPENAI_API_KEY"]:
                st.session_state.available_models.append("openai/gpt-3.5-turbo")

        if "ANTHROPIC_API_KEY" in ENV:
            if ENV["ANTHROPIC_API_KEY"]:
                st.session_state.available_models.append("anthropic/claude-2")

        if len(st.session_state.available_models) == 0:
            st.error("No models available. Please check your API keys.")
            st.stop()

    if "model_select" not in st.session_state:
        st.session_state.model_select = st.session_state.available_models[0]

    if "available_personas" not in st.session_state:
        st.session_state.available_personas = get_persona_names()

    if "model_db" not in st.session_state:
        st.session_state.model_db = SentenceTransformerDB()
        st.session_state.model_db.init_from_disk()

    if "model_db" not in st.session_state:
        st.session_state.model_db = SentenceTransformerDB()
        st.session_state.model_db.init_from_disk()

    if "embedding_model" not in st.session_state:
        available_models = []
        for model_name in st.session_state.model_db:
            available_models.append(model_name)

        default_model = available_models[0]

        st.session_state.embedding_model = st.session_state.model_db[default_model]

    if "BUCKET_NAME" not in st.session_state:
        st.session_state.BUCKET_NAME = f"redbox-storage-{st.session_state.user_uuid}"

        try:
            st.session_state.s3_client.head_bucket(Bucket=st.session_state.BUCKET_NAME)
        except ClientError as err:
            # The bucket does not exist or you have no access.
            if err.response["Error"]["Code"] == "404":
                print("The bucket does not exist.")
                st.session_state.s3_client.create_bucket(Bucket=st.session_state.BUCKET_NAME)
                print("Bucket created successfully.")
            else:
                raise err

    if "storage_handler" not in st.session_state:
        es = Elasticsearch(
            hosts=[
                {
                    "host": ENV["ELASTIC_HOST"],
                    "port": int(ENV["ELASTIC_PORT"]),
                    "scheme": ENV["ELASTIC_SCHEME"],
                }
            ],
            basic_auth=(ENV["ELASTIC_USER"], ENV["ELASTIC_PASSWORD"]),
        )
        st.session_state.storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")

    if st.session_state.user_uuid == "dev":
        st.sidebar.info("**DEV MODE**")
        with st.sidebar.expander("⚙️ DEV Settings", expanded=False):
            st.session_state.model_params = {
                # TODO: This shoudld be dynamic to the model
                "max_tokens": st.number_input(
                    label="max_tokens",
                    min_value=0,
                    max_value=100_000,
                    value=1024,
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
                load_llm_handler(ENV=ENV)

            if st.button(label="Empty Streamlit Cache"):
                st.cache_data.clear()

    else:
        _model_params = {"max_tokens": 4096, "temperature": 0.2}

    if "llm" not in st.session_state or "llm_handler" not in st.session_state:
        load_llm_handler(
            ENV=ENV,
        )

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


def get_link_html(page: str, text: str, query_dict: Optional[dict] = None, target: str = "_self") -> str:
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


def get_file_link(file: File, page: Optional[int] = None) -> str:
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
        query_dict["page_number"] = page

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


def load_llm_handler(ENV, update=False) -> None:
    """Loads the LLM and LLMHandler into the session state

    Args:
        ENV (_type_): the environment variables dictionary
        model_params (_type_): the model parameters

    """

    st.session_state.llm = ChatLiteLLM(
        model=st.session_state.model_select,
        max_tokens=st.session_state.model_params["max_tokens"],
        temperature=st.session_state.model_params["temperature"],
        streaming=True,
    )

    if "llm_handler" not in st.session_state or update:
        embedding_function = SentenceTransformerEmbeddings()

        vector_store = ElasticsearchStore(
            es_url=f"{ENV['ELASTIC_SCHEME']}://{ENV['ELASTIC_HOST']}:{ENV['ELASTIC_PORT']}",
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


def hash_list_of_files(list_of_files: list[File]) -> str:
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
        stream = st.session_state.s3_client.get_object(Bucket=st.session_state.BUCKET_NAME, Key=file.name)
        file_bytes = stream["Body"].read()
        render_method(file, file_bytes)

    def _render_pdf(self, file: File, page_number: Optional[int] = None) -> None:
        stream = st.session_state.s3_client.get_object(Bucket=st.session_state.BUCKET_NAME, Key=file.name)
        base64_pdf = base64.b64encode(stream["Body"].read()).decode("utf-8")

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

    def _render_txt(self, file: File, file_bytes: bytes) -> None:
        st.markdown(f"{file_bytes.decode('utf-8')}", unsafe_allow_html=True)

    def _render_xlsx(self, file: File, file_bytes: bytes) -> None:
        df = pd.read_excel(BytesIO(file_bytes))
        st.dataframe(df, use_container_width=True)

    def _render_csv(self, file: File, file_bytes: bytes) -> None:
        df = pd.read_csv(BytesIO(file_bytes))
        st.dataframe(df, use_container_width=True)

    def _render_eml(self, file: File, file_bytes: bytes) -> None:
        st.markdown(self.cleaner.clean_html(file_bytes.decode("utf-8")), unsafe_allow_html=True)

    def _render_html(self, file: File, file_bytes: bytes) -> None:
        markdown_html = html2markdown.convert(file_bytes.decode("utf-8"))
        st.markdown(markdown_html, unsafe_allow_html=True)

    def _render_docx(self, file: File, file_bytes: bytes) -> None:
        st.warning("DOCX preview not yet supported.")
        st.download_button(
            label=file.name,
            data=file_bytes,
            mime="application/msword",
            file_name=file.name,
        )


def replace_doc_ref(
    output_for_render: str = "",
    files: Optional[list[File]] = None,
    page_numbers: Optional[list] = None,
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
    files = files or []
    page_numbers = page_numbers or []

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
    feedback: dict,
    input: str | list[str],
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


chat_personas = [
    ChatPersona(
        name="Policy Experts",
        description="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua",
        prompt="Lorem ipsum",
    ),
    ChatPersona(
        name="Economists",
        description="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna",
        prompt="Lorem ipsum",
    ),
    ChatPersona(
        name="Foreign Policy Experts",
        description="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore",
        prompt="Lorem ipsum",
    ),
]


def get_persona_names() -> list:
    """Returns list of persona names"""
    persona_names = []
    for chat_persona in chat_personas:
        persona_names.append(chat_persona.name)
    return persona_names


def get_persona_description(persona_name) -> str:
    """Returns persona description based on persona name selected by user

    Args:
        persona_name (str): Persona name selected by user.
    """
    for chat_persona in chat_personas:
        if chat_persona.name == persona_name:
            return chat_persona.description


def get_persona_prompt(persona_name) -> str:
    """Returns persona prompt based on persona name selected by user

    Args:
        persona_name (str): Persona name selected by user.
    """
    for chat_persona in chat_personas:
        if chat_persona.name == persona_name:
            return chat_persona.prompt
