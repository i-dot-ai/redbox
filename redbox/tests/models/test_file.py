from redbox.models.file import Metadata, Link


def test_merge():
    left = Metadata(languages=["en"], page_number=1, links=[Link(text="text", start_index=1, url="http://url")])
    right = Metadata(languages=["en", "fr"], page_number=[2, 3])

    expected = Metadata(
        languages=["en", "fr"],
        link_texts=[],
        link_urls=[],
        links=[Link(text="text", url="http://url", start_index=1)],
        page_number=[1, 2, 3],
    )
    actual = Metadata.merge(left, right)

    assert actual == expected
