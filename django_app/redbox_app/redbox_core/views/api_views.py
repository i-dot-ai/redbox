import logging
from http import HTTPStatus
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.fields import CharField, FileField, IntegerField, ListField, UUIDField
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from redbox import Redbox
from redbox_app.redbox_core import error_messages
from redbox_app.redbox_core.models import ChatMessage, File, get_chat_session
from redbox_app.redbox_core.utils import sanitize_json

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

    def to_internal_value(self, data):
        data = sanitize_json(data)
        return super().to_internal_value(data)

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


class ChatMessageSerializer(Serializer):
    message = CharField()
    chat_backend_id = UUIDField(required=False)
    temperature = IntegerField(required=False)


class ChatMessageView(APIView):
    redbox = Redbox(debug=settings.DEBUG)

    def post(self, request, chat_id: UUID):
        serializer = ChatMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            chat = get_chat_session(chat_id=chat_id, user=request.user, data=serializer.validated_data)
        except ValueError as e:
            return Response({"non_field_errors": e.args[0]}, status=status.HTTP_400_BAD_REQUEST)

        state = chat.to_langchain()

        try:
            state = self.redbox.run_sync(state)

            message = ChatMessage.objects.create(
                chat=chat,
                text=state.content,
                role=ChatMessage.Role.ai,
            )

            return Response(
                {"message_id": message.id, "title": chat.name, "session_id": chat.id}, status=status.HTTP_200_OK
            )

        except BaseException:  # noqa: BLE001
            return Response({"non_field_error": error_messages.CORE_ERROR_MESSAGE}, status=status.HTTP_200_OK)
