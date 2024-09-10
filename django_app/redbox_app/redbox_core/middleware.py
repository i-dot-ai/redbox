import json

from asgiref.sync import iscoroutinefunction
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import sync_and_async_middleware


@sync_and_async_middleware
def nocache_middleware(get_response):
    if iscoroutinefunction(get_response):

        async def middleware(request: HttpRequest) -> HttpResponse:
            response = await get_response(request)
            response["Cache-Control"] = "no-store"
            return response
    else:

        def middleware(request: HttpRequest) -> HttpResponse:
            response = get_response(request)
            response["Cache-Control"] = "no-store"
            return response

    return middleware


@sync_and_async_middleware
def security_header_middleware(get_response):
    report_to = json.dumps(
        {
            "group": "csp-endpoint",
            "max_age": 10886400,
            "endpoints": [{"url": settings.SENTRY_REPORT_TO_ENDPOINT}],
            "include_subdomains": True,
        },
        indent=None,
        separators=(",", ":"),
        default=str,
    )

    if iscoroutinefunction(get_response):

        async def middleware(request: HttpRequest) -> HttpResponse:
            response = await get_response(request)
            if settings.SENTRY_REPORT_TO_ENDPOINT:
                response["Report-To"] = report_to
            return response
    else:

        def middleware(request: HttpRequest) -> HttpResponse:
            response = get_response(request)
            if settings.SENTRY_REPORT_TO_ENDPOINT:
                response["Report-To"] = report_to
            return response

    return middleware


@sync_and_async_middleware
def plotly_no_csp_no_xframe_middleware(get_response):
    if iscoroutinefunction(get_response):

        async def middleware(request: HttpRequest) -> HttpResponse:
            response = await get_response(request)
            if "admin/report" in request.path:
                response.headers.pop("Content-Security-Policy", None)
                response.headers.pop("X-Frame-Options", None)
            return response
    else:

        def middleware(request: HttpRequest) -> HttpResponse:
            response = get_response(request)
            if "admin/report" in request.path:
                response.headers.pop("Content-Security-Policy", None)
                response.headers.pop("X-Frame-Options", None)
            return response

    return middleware
