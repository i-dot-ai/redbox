from django.conf import settings


def compression_enabled(_request):
    """we want to turn compression off during testing"""
    return {"COMPRESSION_ENABLED": settings.COMPRESSION_ENABLED}


def environment(_request):
    """we want to be able to have code present different in different ENVs"""
    return {"ENVIRONMENT": settings.ENVIRONMENT}
