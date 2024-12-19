from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.fields import FileField, UUIDField
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from redbox_app.redbox_core.models import File
from redbox_app.redbox_core.serializers import UserSerializer

User = get_user_model()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_view_pre_alpha(request):
    """this is for testing and evaluation only
    this *will* change so that not all data is returned!
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class UploadSerializer(Serializer):
    file = FileField()
    chat_id = UUIDField()

    class Meta:
        fields = "__all__"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def file_upload(request):
    """upload a new file"""

    serializer = UploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    file = File.objects.create(
        user=request.user, original_file=serializer.validated_data["file"], chat_id=serializer.validated_data["chat_id"]
    )
    return Response({"file_id": file.id}, status=200)
