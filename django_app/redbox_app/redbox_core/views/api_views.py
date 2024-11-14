from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from redbox_app.redbox_core.serializers import UserSerializer

User = get_user_model()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_view(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)
