from logging import getLogger
from typing_extensions import Generator
from pathlib import Path
import csv

from .cases import AITestCase

TEST_CASES_FILE = Path("data/cases.csv")
DOCUMENTS_DIR = Path("data/documents")
DOCUMENT_UPLOAD_USER = "ai_tests"

logger = getLogger()


def test_cases() -> Generator[None, None, AITestCase]:
    with open(f"{TEST_CASES_FILE}") as cases_file:
        reader = csv.DictReader(cases_file)
        all_cases = [
            AITestCase(
                id=row["ID"],
                prompts=row["Prompts"].split("|"),
                documents=[f"{DOCUMENT_UPLOAD_USER}/{doc_name}" for doc_name in row["Documents"].split("|")],
            )
            for row in reader
        ]
    missing_documents = set(d for case in all_cases for d in case.documents) - set(
        d.name for d in DOCUMENTS_DIR.iterdir()
    )
    if len(missing_documents) > 0:
        logger.warning(f"Missing {len(missing_documents)} documents - {",".join(missing_documents)}")
    return all_cases


def pytest_generate_tests(metafunc):
    if "test_case" in metafunc.fixturenames:
        metafunc.parametrize("test_case", test_cases(), ids=lambda t: t.id)
