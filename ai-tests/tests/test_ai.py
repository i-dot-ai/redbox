from pathlib import Path
import sys
from uuid import uuid4
import json

from langfuse.callback import CallbackHandler
import pytest

from redbox.models.settings import Settings, get_settings
from redbox.models.chain import RedboxQuery, RedboxState, AISettings, ChatLLMBackend
from redbox.app import Redbox
from redbox.loader.ingester import ingest_file

from .cases import AITestCase
from .conftest import DOCUMENT_UPLOAD_USER, DOCUMENTS_DIR, OUTPUTS_DIR


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

@pytest.fixture(params=[
    AISettings().chat_backend,
    ChatLLMBackend(name="anthropic.claude-3-sonnet-20240229-v1:0", provider="bedrock")
],
ids=[
    "default",
    "claude"
])
def ai_settings(request):
    return AISettings(
        chat_backend=request.param
    )


def get_state(user_uuid, prompts, documents, ai_settings):
    q = RedboxQuery(
        question=f"@gadget {prompts[-1]}",
        s3_keys=documents,
        user_uuid=user_uuid,
        chat_history=prompts[:-1],
        ai_settings=ai_settings,
        permitted_s3_keys=documents,
    )

    return RedboxState(
        request=q,
    )


def run_app(app, state) -> RedboxState:
    langfuse_handler = CallbackHandler()
    return RedboxState.model_validate(app.graph.invoke(state, config={"callbacks": [langfuse_handler]}))


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
    for doc in DOCUMENTS_DIR.iterdir():
        uri = f"{DOCUMENT_UPLOAD_USER}/{doc.name}"
        if uri not in all_loaded_doc_uris:
            print(f"Loading missing document: {uri}")
            file_to_s3(doc, settings.s3_client(), settings)
            ingest_file(uri)
    return all_loaded_doc_uris


@pytest.fixture(scope="session")
def logs_dir():
    p = OUTPUTS_DIR / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture(scope="session")
def responses_dir():
    p = OUTPUTS_DIR / "responses"
    p.mkdir(parents=True, exist_ok=True)
    return p


def test_usecases(test_case: AITestCase, loaded_docs: set[str], ai_settings, logs_dir, responses_dir):
    env = get_settings()
    app = Redbox(debug=True, env=env)

    logs_path = logs_dir / test_case.id
    response_path = responses_dir / test_case.id
    citations_path = responses_dir / (test_case.id + "_citations.json")

    redbox_state = get_state(
        user_uuid=uuid4(), 
        prompts=test_case.prompts, 
        documents=test_case.documents, 
        ai_settings=ai_settings
    )

    with open(logs_path, "w") as file:
        sys.stdout = file
        final_state = run_app(app, redbox_state)
    with open(response_path, "w") as file:
        file.write(final_state.last_message.content)
    with open(citations_path, "w") as file:
        citations_list = [c.model_dump(mode="json") for c in final_state.citations]
        json.dump(citations_list, fp=file, indent=2)

