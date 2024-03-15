from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def homepage_view(request):
    return render(
        request,
        template_name="homepage.html",
        context={"request": request},
    )


def documents_view(request):
    # Testing with some static docs for now
    documents = [
        {"id": "doc-id-1", "name": "Document 1", "url": "#download1", "processed": True, "process_status": "Complete"},
        {"id": "doc-id-2", "name": "Document 2", "url": "#download2", "processed": False, "process_status": "2/5 Parsing"},
    ]
    return render(
        request,
        template_name="documents.html",
        context={"request": request, "documents": documents},
    )


def upload_view(request):
    if request.method == "POST" and request.FILES["uploadDoc"]:
        doc = request.FILES["uploadDoc"]
        print(doc)
        # TO DO: handle file upload here
    return render(
        request,
        template_name="upload.html",
        context={"request": request},
    )


def remove_doc_view(request, doc_id: str):
    if request.method == "POST":
        print(f"Removing document: {request.POST['doc_id']}")
        # TO DO: handle document deletion here

    # Hard-coding document name for now, just to flag that this is needed in the template
    doc_name = "Document X"
    return render(
        request,
        template_name="remove-doc.html",
        context={"request": request, "doc_id": doc_id, "doc_name": doc_name},
    )