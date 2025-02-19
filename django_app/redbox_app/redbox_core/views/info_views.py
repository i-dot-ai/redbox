"""
Views for info pages like privacy notice, accessibility statement, etc.
These shouldn't contain sensitive data and don't require login.
"""

import waffle
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def privacy_notice_view(request):
    return render(
        request,
        "privacy-notice.html",
        {
            "waffle_flag": waffle.flag_is_active,
        },
    )


@require_http_methods(["GET"])
def cookies_view(request):
    return render(request, "cookies.html", {})


@require_http_methods(["GET"])
def support_view(request):
    return render(
        request, "support.html", {"contact_email": settings.CONTACT_EMAIL, "version": settings.REDBOX_VERSION}
    )


@require_http_methods(["GET"])
def accessibility_statement_view(request):
    return render(
        request,
        "accessibility-statement.html",
        {
            "contact_email": settings.CONTACT_EMAIL,
            "waffle_flag": waffle.flag_is_active,
        },
    )
