from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.django_db()
def test_0012_alter_file_status(migrator):
    old_state = migrator.apply_initial_migration(("redbox_core", "0012_alter_file_status"))

    original_file = SimpleUploadedFile("original_file.txt", b"Lorem Ipsum.")

    User = old_state.apps.get_model("redbox_core", "User")
    ChatHistory = old_state.apps.get_model("redbox_core", "ChatHistory")
    ChatMessage = old_state.apps.get_model("redbox_core", "ChatMessage")
    File = old_state.apps.get_model("redbox_core", "File")

    user = User.objects.create(email="someone@example.com")
    chat_history = ChatHistory.objects.create(users=user)
    chat_message = ChatMessage.objects.create(chat_history=chat_history, text="hello", role="user")

    file = File.objects.create(
        user=user, original_file=original_file, original_file_name=original_file.name, core_file_uuid=uuid4()
    )
    chat_message.source_files.set([file])
    chat_message.save()

    assert chat_message.source_files.first().pk == file.pk
    new_state = migrator.apply_tested_migration(
        ("redbox_core", "0013_chatmessage_selected_files_and_more"),
    )
    NewChatMessage = new_state.apps.get_model("redbox_core", "ChatMessage")  # noqa: N806

    new_chat_message = NewChatMessage.objects.get(pk=chat_message.pk)
    assert new_chat_message.source_files.first().pk == file.pk

    # Cleanup:
    migrator.reset()


@pytest.mark.django_db()
def test_0019_remove_chatmessage_source_files_textchunk_and_more(migrator):
    old_state = migrator.apply_initial_migration(("redbox_core", "0018_chatmessage_route"))

    original_file = SimpleUploadedFile("original_file.txt", b"Lorem Ipsum.")

    User = old_state.apps.get_model("redbox_core", "User")
    ChatHistory = old_state.apps.get_model("redbox_core", "ChatHistory")
    ChatMessage = old_state.apps.get_model("redbox_core", "ChatMessage")
    File = old_state.apps.get_model("redbox_core", "File")

    user = User.objects.create(email="someone@example.com")
    chat_history = ChatHistory.objects.create(users=user)
    chat_message = ChatMessage.objects.create(chat_history=chat_history, text="hello", role="user")

    file = File.objects.create(
        user=user, original_file=original_file, original_file_name=original_file.name, core_file_uuid=uuid4()
    )
    chat_message.source_files.set([file])
    chat_message.save()

    assert chat_message.source_files.first().pk == file.pk
    new_state = migrator.apply_tested_migration(
        ("redbox_core", "0019_remove_chatmessage_source_files_textchunk_and_more"),
    )
    NewChatMessage = new_state.apps.get_model("redbox_core", "ChatMessage")  # noqa: N806
    TextChunk = new_state.apps.get_model("redbox_core", "TextChunk")

    new_chat_message = NewChatMessage.objects.get(pk=chat_message.pk)
    assert new_chat_message.source_files.first().pk == file.pk
    assert new_chat_message.old_source_files.first().pk == file.pk

    assert TextChunk.objects.count() == 1
    text_chunk = TextChunk.objects.first()
    assert text_chunk.file.pk == file.pk
    assert text_chunk.chat_message.pk == new_chat_message.pk

    # Cleanup:
    migrator.reset()
