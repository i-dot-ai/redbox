from asgiref.sync import iscoroutinefunction
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
