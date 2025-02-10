import logging
from http import HTTPStatus
from uuid import UUID

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.fields import CharField, FileField, IntegerField, ListField, UUIDField
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from redbox_app.redbox_core.models import ChatMessage, File

User = get_user_model()
logger = logging.getLogger(__name__)


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
        original_file=serializer.validated_data["file"],
        chat_id=serializer.validated_data["chat_id"],
        status=File.Status.processing,
    )
    file.ingest()
    return Response({"file_id": file.id}, status=200)


class RatingSerializer(Serializer):
    rating = IntegerField()
    text = CharField(required=False)
    chips = ListField(child=CharField(), required=False)

    class Meta:
        fields = "__all__"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def rate_chat_message(request, message_id: UUID):
    serializer = RatingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    logger.info("getting chat-message with id=%s", message_id)

    message: ChatMessage = get_object_or_404(ChatMessage, id=message_id)

    message.rating = serializer.validated_data["rating"]
    message.rating_text = serializer.validated_data.get("text")
    message.rating_chips = sorted(serializer.validated_data.get("chips", []))
    message.save()
    return Response({}, status=HTTPStatus.OK)
