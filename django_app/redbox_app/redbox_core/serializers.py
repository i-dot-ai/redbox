from rest_framework import serializers

from redbox_app.redbox_core.models import Chat, ChatMessage, File, User


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ("unique_name",)


class ChatMessageSerializer(serializers.ModelSerializer):
    selected_files = FileSerializer(many=True, read_only=True)
    source_files = FileSerializer(many=True, read_only=True)

    class Meta:
        model = ChatMessage
        fields = (
            "id",
            "created_at",
            "text",
            "role",
            "route",
            "selected_files",
            "source_files",
            "rating",
            "rating_text",
            "rating_chips",
        )


class ChatSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Chat
        fields = ("name", "messages")


class UserSerializer(serializers.ModelSerializer):
    chats = ChatSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ("is_staff", "business_unit", "grade", "email", "ai_experience", "profession", "chats")
