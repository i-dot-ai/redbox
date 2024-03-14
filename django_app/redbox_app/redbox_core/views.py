from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def homepage_view(request):
    return render(
        request,
        template_name="homepage.html",
        context={"request": request},
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
