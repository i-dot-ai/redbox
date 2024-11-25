from pathlib import Path
import sys
from uuid import uuid4

from langfuse.callback import CallbackHandler
import pytest

from redbox.models.settings import Settings, get_settings
from redbox.models.chain import RedboxQuery, RedboxState, AISettings
from redbox.app import Redbox
from redbox.loader.ingester import ingest_file

from .cases import AITestCase
from .conftest import DOCUMENT_UPLOAD_USER


def file_to_s3(file_path: Path, s3_client, env: Settings) -> str:
    file_name = f"{DOCUMENT_UPLOAD_USER}/{file_path.name}"
    file_type = file_path.suffix

    with file_path.open("rb") as f:
        s3_client.put_object(
            Bucket=env.bucket_name,
            Body=f.read(),
            Key=file_name,
            Tagging=f"file_type={file_type}",
        )

    return file_name


def get_state(user_uuid, prompts, documents):
    q = RedboxQuery(
        question=f"@gadget {prompts[-1]}",
        s3_keys=documents,
        user_uuid=user_uuid,
        chat_history=prompts[:-1],
        ai_settings=AISettings(),
        permitted_s3_keys=documents,
    )

    return RedboxState(
        request=q,
    )


def run_app(app, state) -> RedboxState:
    langfuse_handler = CallbackHandler()
    return app.graph.invoke(state, config={"callbacks": [langfuse_handler]})


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def all_loaded_doc_uris(settings: Settings):
    es = settings.elasticsearch_client()
    response = es.search(
        index=f"{settings.elastic_root_index}-chunk-current", query={"term": {"metadata.chunk_resolution": "largest"}}
    )
    hits = response.get("hits", {}).get("hits", [])
    return set(d["_source"]["metadata"]["uri"] for d in hits)


@pytest.fixture
def loaded_docs(all_loaded_doc_uris: set[str], settings: Settings):
    for doc in Path("data/documents").iterdir():
        uri = f"{DOCUMENT_UPLOAD_USER}/{doc.name}"
        if uri not in all_loaded_doc_uris:
            print(f"Loading missing document: {uri}")
            file_to_s3(doc, settings.s3_client(), settings)
            ingest_file(uri)
    return all_loaded_doc_uris


def test_usecases(test_case: AITestCase, loaded_docs: set[str], output_dir: Path = Path("data/output")):
    env = get_settings()
    app = Redbox(debug=True, env=env)

    save_path = output_dir / test_case.id
    # call agent
    try:
        redbox_state = get_state(user_uuid=uuid4(), prompts=test_case.prompts, documents=test_case.documents)
        with open(save_path, "w") as file:
            sys.stdout = file
            run_app(app, redbox_state)

    except Exception as e:
        print(f"Error in {e}")
