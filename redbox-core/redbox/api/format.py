from langchain_core.documents.base import Document


def format_documents(documents: list[Document]) -> str:
    formatted: list[str] = []
    for d in documents:
        doc_xml = (
            f"<Document>\n"
            f"\t<SourceType>{d.metadata.get("creator_type", "Unknown")}</SourceType>\n"
            f"\t<Source>{d.metadata.get("uri", "")}</Source>\n"
            "\t<Content>\n"
            f"{d.page_content}\n"
            "\t</Content>\n"
            f"</Document>"
        )
        formatted.append(doc_xml)

    return "\n\n".join(formatted)
