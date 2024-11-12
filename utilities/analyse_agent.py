import argparse
import datetime
import io
import logging
import re
import sys
from datetime import timezone
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, NotRequired, Required
from uuid import UUID, uuid4

from dotenv import load_dotenv
from elasticsearch.helpers import scan
from langchain_core.documents import Document
from langchain_core.runnables import RunnableParallel
from langfuse.decorators import observe
from langgraph.managed.is_last_step import RemainingStepsManager
from pandas import DataFrame, read_csv

from redbox.app import Redbox
from redbox.chains.ingest import ingest_from_loader
from redbox.loader.ingester import get_elasticsearch_store, ingest_file
from redbox.loader.loaders import MetadataLoader, UnstructuredChunkLoader
from redbox.models import Settings
from redbox.models.chain import (AISettings, Citation, DocumentState,
                                 LLMCallMetadata, RedboxQuery, RedboxState,
                                 RequestMetadata, Source, ToolState,
                                 document_reducer, metadata_reducer,
                                 tool_calls_reducer)
from redbox.models.file import ChunkResolution
from redbox.models.settings import ChatLLMBackend, Settings
from redbox.retriever.queries import build_query_filter

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object
logging.basicConfig(
    filename="/Users/saisakulchernbumroong/Documents/langchain_graph_output.log",
    level=logging.DEBUG,
)

load_dotenv(dotenv_path="../tests/.env.test")


# global
env = Settings(object_store="minio")
alias = env.elastic_chunk_alias


def make_file_query(file_name: str, resolution: ChunkResolution | None = None) -> dict[str, Any]:
    query_filter = build_query_filter(
        selected_files=[file_name],
        permitted_files=[file_name],
        chunk_resolution=resolution,
    )
    return {"query": {"bool": {"must": [{"match_all": {}}], "filter": query_filter}}}


def file_to_s3(file_path: Path, s3_client: S3Client, env: Settings) -> str:
    file_name = file_path.name
    file_type = file_path.suffix

    with file_path.open("rb") as f:
        s3_client.put_object(
            Bucket=env.bucket_name,
            Body=f.read(),
            Key=file_name,
            Tagging=f"file_type={file_type}",
        )

    return file_name


def extract_text_between_patterns(text):
    # Updated regex to match markers with any characters after 'p_', 's_', or 'd_' until '->'
    pattern = r"(- [psd]_[\w]+ ->)(.*?)(?=- [psd]_[\w]+ ->|$)"

    # Find all matches in the text
    matches = re.findall(pattern, text, re.DOTALL)

    # Process and clean matches
    extracted_data = []
    for marker, content in matches:
        marker_name = marker.split()[1]  # Extract p_{anything}, s_{anything}, or d_{anything}
        extracted_data.append((marker_name, content.strip()))

    return extracted_data


def read_use_cases(prompts_file, documents_file):
    return read_csv(prompts_file, header=0), read_csv(documents_file, header=0)


def get_user_doc(documents, user_id):
    return documents.loc[documents.User == user_id, "Documents"].tolist()


def get_user_prompts(prompts: DataFrame, user_id):
    return prompts.loc[prompts.User == user_id, "Prompts"].tolist()


def temp_ingest_file(file_name: str, es_index_name: str = alias) -> str | None:
    logging.info("Ingesting file: %s", file_name)

    es = env.elasticsearch_client()

    if es_index_name == alias:
        if not es.indices.exists_alias(name=alias):
            print("The alias does not exist")
            print(alias)
            print(es.indices.exists_alias(name=alias))
            # create_alias(alias)
    else:
        es.options(ignore_status=[400]).indices.create(index=es_index_name)

    # Extract metadata
    metadata_loader = MetadataLoader(env=env, s3_client=env.s3_client(), file_name=file_name)
    metadata = metadata_loader.extract_metadata()

    chunk_ingest_chain = ingest_from_loader(
        loader=UnstructuredChunkLoader(
            chunk_resolution=ChunkResolution.normal,
            env=env,
            min_chunk_size=env.worker_ingest_min_chunk_size,
            max_chunk_size=env.worker_ingest_max_chunk_size,
            overlap_chars=0,
            metadata=metadata,
        ),
        s3_client=env.s3_client(),
        vectorstore=get_elasticsearch_store(es, es_index_name),
        env=env,
    )

    try:
        new_ids = RunnableParallel({"normal": chunk_ingest_chain}).invoke(file_name)
        logging.info(
            "File: %s %s chunks ingested",
            file_name,
            {k: len(v) for k, v in new_ids.items()},
        )
    except Exception as e:
        logging.exception("Error while processing file [%s]", file_name)
        return f"{type(e)}: {e.args[0]}"


class User:
    user_id: int
    user_uuid: UUID
    documents: list[str]
    # s3_permission: list[str] Assuming this is the same as uploaded docs
    prompts: list

    def __init__(self, user_id, user_uuid, documents, prompts) -> None:
        self.user_id = user_id
        self.user_uuid = user_uuid
        self.documents = documents
        # self.s3_permission = s3_permission Assuming this is the same as uploaded docs
        self.prompts = prompts

    def has_been_uploaded(self, file_path) -> bool:
        # check if uploaded_documents have been added before
        file_query = make_file_query(file_name=file_path.name, resolution=ChunkResolution.normal)
        es_client = env.elasticsearch_client()
        chunks = list(scan(client=es_client, index=env.elastic_chunk_alias, query=file_query))
        return len(chunks) > 0

    def upload_file(self):
        # upload file if have not been uploaded
        for file_path in self.documents:
            if not self.has_been_uploaded(Path(file_path)):
                filename = file_to_s3(file_path=Path(file_path), s3_client=env.s3_client(), env=env)
                temp_ingest_file(filename)


def get_state(user_id, prompt, documents):
    q = RedboxQuery(
        question=f"@gadget {prompt}",
        s3_keys=documents,
        user_uuid=user_id,
        chat_history=[],
        ai_settings=AISettings(rag_k=3),
        permitted_s3_keys=documents,
    )

    return RedboxState(
        request=q,
    )


def read_clean(filename):
    f = open(filename, "r")
    output = f.read()
    # Define a regex pattern to match ANSI escape codes
    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", output)


def write_response(filename, user: User, prompt, response):
    prompts = read_csv(filename)
    prompts.loc[(prompts.User == user.user_id) & (user.prompts == prompt), "Response"] = response
    prompts.to_csv(filename)


def change_route_to_text(text):
    # Regular expression to extract the key and its value
    pattern = r"'([^']+)':\s*<([^>]+)>"

    # Find matches
    match = re.search(pattern, text)
    if match:
        return re.sub(pattern, f'{match.group(1)}: "<{match.group(2)}>"', text)
    else:
        return text


def extract_state(text):
    """
    Extracts state content after '[X:checkpoint] State at the end of step X:' and parses it to dict.
    Handles additional text that might follow the state content.

    Args:
        text (str): Input text containing state information

    Returns:
        dict: Parsed state content, or None if not found or invalid format
    """
    if len(text) > 0:
        # try end state
        found = re.search(r"State at the end of step", text)
        if found:
            text = text[found.start() :]

        match = re.search(r"{", text)
        start_pos = match.start()

        if text[start_pos] != "{":
            return None

        # Track bracket nesting
        bracket_count = 1
        end_pos = start_pos + 1

        # Find the matching closing bracket
        while end_pos < len(text) and bracket_count > 0:
            if text[end_pos] == "{":
                bracket_count += 1
            elif text[end_pos] == "}":
                bracket_count -= 1
            end_pos += 1

        if bracket_count != 0:
            return None
        else:
            return text[start_pos:end_pos]
    else:
        return ""


def convert_to_dict(text):
    content = change_route_to_text(extract_state(text))
    try:
        safe_dict = {
            "datetime": datetime,
            "timezone": timezone,
            "timestamp": lambda **kwargs: kwargs,
            "ChatLLMBackend": ChatLLMBackend,
            "RequestMetadata": RequestMetadata,
            "LLMCallMetadata": LLMCallMetadata,
            "Document": Document,
            "UUID": UUID,
            "RedboxQuery": RedboxQuery,
            "AISettings": AISettings,
            "request": Required[RedboxQuery],
            "documents": Annotated[NotRequired[DocumentState], document_reducer],
            "text": NotRequired[str | None],
            "route_name": NotRequired[str | None],
            "tool_calls": Annotated[NotRequired[ToolState], tool_calls_reducer],
            "metadata": Annotated[NotRequired[RequestMetadata], metadata_reducer],
            "citations": NotRequired[list[Citation] | None],
            "steps_left": Annotated[NotRequired[int], RemainingStepsManager],
            "chunk_resolution": ChunkResolution,
            "Citation": Citation,
            "Source": Source,
        }

        # Clean up the string and evaluate it
        cleaned_content = content.strip()
        return eval(cleaned_content, {"__builtins__": {}}, safe_dict)

    except Exception as e:
        print("-----------------------------")
        print(cleaned_content)
        print(f"Error parsing state: {e}")
        return {}

def run_usecases(prompts_file, documents_file, save_path, selected_case=[], extract=False):
    print(f"Running search on {prompts_file}")
    prompts, documents = read_use_cases(prompts_file, documents_file)

    users = selected_case if selected_case else prompts.User.unique()

    for user_id in users:
        user = User(
            user_id=user_id,
            user_uuid=uuid4(),
            documents=get_user_doc(documents, user_id),
            prompts=get_user_prompts(prompts, user_id),
        )

        # upload files
        user.upload_file()

        # start Redbox
        buffer = io.StringIO()
        sys.stdout = buffer
        app = Redbox(debug=True, env=env)

        # call agent
        for prompt in user.prompts:
            try:
                x = get_state(user.user_uuid, prompt, user.documents)
                # response = await app.run(x)

                response = app.graph.invoke(x)
                # print(f'Tuck {response["output"]}')
                sys.stdout = sys.__stdout__

                # Retrieve the verbose output from the buffer
                verbose_output = buffer.getvalue()
                # Save full verbose output to a separate file
                with open(
                    save_path,
                    "w",
                ) as file:
                    file.write(verbose_output)

                # print(f'here is response {response}')

                if extract:
                    extract_save(
                        verbose_output,
                        save_path.replace("txt", "csv"),
                    )

                print("LangChain verbose output processed and saved.")
            except Exception as e:
                print(f"Error in {e}")


def extract_save(filename, savepath):
    print(f"Running extract on {filename}, saving to {savepath}")
    clean_content = read_clean(filename)
    df = DataFrame()
    for s in extract_text_between_patterns(clean_content):
        extract_dict = convert_to_dict(s[1])
        df2 = {
            "Node": s[0],
            "request": extract_dict.get("request", ""),
            "steps_left": extract_dict.get("steps_left", ""),
            "documents": extract_dict.get("documents", ""),
            "metadata": extract_dict.get("metadata", ""),
            "text": extract_dict.get("text", ""),
            "tool_calls": extract_dict.get("tool_calls", ""),
            "citations": extract_dict.get("citations", ""),
            "content": s[1],
        }
        df = df._append(df2, ignore_index=True)
    df.to_csv(savepath)


def main():
    parser = argparse.ArgumentParser(description="Run different functions based on user input.")

    # Create subparsers for the different commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Subparser for the `search` command
    parser_run_usecases = subparsers.add_parser("run_usecases", help="Run Redbox on given use cases.")
    parser_run_usecases.add_argument("-f", "--filename", required=True, help="The filename contains use cases.")
    parser_run_usecases.add_argument("-d", "--document", required=True, help="The filename contains user documents.")
    parser_run_usecases.add_argument(
        "-id",
        "--selected_case",
        required=False,
        help="A list of user id to run use cases.",
    )
    parser_run_usecases.add_argument("-s", "--savepath", required=True, help="The path to save the log file.")
    parser_run_usecases.add_argument("-ex", "--extract", required=False, help="True if log extraction is required.")

    # Subparser for the `extract` command
    parser_extract = subparsers.add_parser("extract", help="Extracting information from log file")
    parser_extract.add_argument("-f", "--filename", required=True, help="The filename to extract")
    parser_extract.add_argument("-s", "--savepath", required=True, help="The path to save the extraction")

    args = parser.parse_args()

    if args.command == "run_usecases":
        run_usecases(
            prompts_file=args.filename,
            documents_file=args.document,
            save_path=args.savepath,
            selected_case=[int(i) for i in args.selected_case.split(",")],
            extract=args.extract,
        )
    elif args.command == "extract":
        extract_save(args.filename, args.savepath)
    else:
        parser.print_help()


# Run the main function
if __name__ == "__main__":
    main()


""" Example code 
A structured csv files are required to run. These include: 
- prompt.csv containing User which are user id, and Prompts which are prompt query.
- documents.csv containing User which are user id, and Documents which are document file path.

To run use cases from csv file

python /Users/saisakulchernbumroong/Documents/vsprojects/redbox/utilities/analyse_agent.py run_usecases -f '/Users/saisakulchernbumroong/Documents/use_cases.csv' -d '/Users/saisakulchernbumroong/Documents/documents.csv' -id 7 -s '/Users/saisakulchernbumroong/Documents/test_log_7.txt'

To extract data from log

python /redbox/utilities/analyse_agent.py extract -f '/Documents/test_log_7.txt' -s '/Documents/extract_log_7.csv'

"""
