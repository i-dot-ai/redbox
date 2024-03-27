import os

import pytest


@pytest.fixture
def file_pdf_path():
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "pdf",
        "Cabinet Office - Wikipedia.pdf",
    )
    yield path
