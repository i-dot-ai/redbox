from django.shortcuts import render


def sign_in_view(request):
    return render(
        request,
        template_name="sign-in.html",
        context={"request": request},
    )


def sign_in_link_sent_view(request):
    return render(
        request,
        template_name="sign-in-link-sent.html",
        context={"request": request},
    )


def signed_out_view(request):
    return render(
        request,
        template_name="signed-out.html",
        context={"request": request},
    )
