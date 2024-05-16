import uuid

import pytest

from redbox.models.file import Link, Metadata

UUID_1 = uuid.UUID("7c66416e-eff7-441f-aafc-6f06e62fb4ec")
UUID_2 = uuid.UUID("b7aadcce-806c-4dc6-8b95-d2477d717560")


def test_merge_pass():
    left = Metadata(
        languages=["en"],
        page_number=1,
        links=[Link(text="text", start_index=1, url="http://url")],
        parent_doc_uuid=UUID_1,
    )
    right = Metadata(languages=["en", "fr"], page_number=[2, 3])

    expected = Metadata(
        languages=["en", "fr"],
        links=[Link(text="text", url="http://url", start_index=1)],
        page_number=[1, 2, 3],
        parent_doc_uuid=UUID_1,
    )
    actual = Metadata.merge(left, right)

    assert actual == expected


def test_merge_pass_same_parent_doc_uuid():
    left = Metadata(parent_doc_uuid=UUID_1)
    right = Metadata(parent_doc_uuid=UUID_1)

    expected = Metadata(parent_doc_uuid=UUID_1)
    actual = Metadata.merge(left, right)

    assert actual == expected


def test_merge_pass_one_empty_parent_doc_uuid():
    left = Metadata(parent_doc_uuid=UUID_1)
    right = Metadata()

    expected = Metadata(parent_doc_uuid=UUID_1)
    actual = Metadata.merge(left, right)

    assert actual == expected


def test_merge_pass_two_parent_doc_uuid():
    left = Metadata(parent_doc_uuid=UUID_1)
    right = Metadata(parent_doc_uuid=UUID_2)
    with pytest.raises(ValueError) as value_error:
        Metadata.merge(left, right)
    assert value_error.value.args[0] == "chunks do not have the same parent_doc_uuid"
