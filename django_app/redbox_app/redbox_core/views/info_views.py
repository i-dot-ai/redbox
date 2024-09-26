"""
Views for info pages like privacy notice, accessibility statement, etc.
These shouldn't contain sensitive data and don't require login.
"""

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def privacy_notice_view(request):
    if settings.REPO_OWNER.lower() == "uktrade":
        return render(request, "privacy-notice-uktrade.html", {})
    return render(request, "privacy-notice.html", {})


@require_http_methods(["GET"])
def support_view(request):
    if settings.REPO_OWNER.lower() == "uktrade":
        return render(request, "support-uktrade.html", {"contact_email": settings.CONTACT_EMAIL})
    return render(
        request, "support.html", {"contact_email": settings.CONTACT_EMAIL, "version": settings.REDBOX_VERSION}
    )


@require_http_methods(["GET"])
def accessibility_statement_view(request):
    if settings.REPO_OWNER.lower() == "uktrade":
        return render(request, "accessibility-statement-uktrade.html", {"contact_email": settings.CONTACT_EMAIL})
    return render(request, "accessibility-statement.html", {"contact_email": settings.CONTACT_EMAIL})
