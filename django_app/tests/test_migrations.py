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
def test_0020_remove_chatmessage_source_files_textchunk_and_more(migrator):
    old_state = migrator.apply_initial_migration(("redbox_core", "0019_alter_chatmessage_route"))

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
        ("redbox_core", "0020_remove_chatmessage_source_files_textchunk_and_more"),
    )
    NewChatMessage = new_state.apps.get_model("redbox_core", "ChatMessage")  # noqa: N806
    Citation = new_state.apps.get_model("redbox_core", "Citation")

    new_chat_message = NewChatMessage.objects.get(pk=chat_message.pk)
    assert new_chat_message.source_files.first().pk == file.pk
    assert new_chat_message.old_source_files.first().pk == file.pk

    assert Citation.objects.count() == 1
    citation = Citation.objects.first()
    assert citation.file.pk == file.pk
    assert citation.chat_message.pk == new_chat_message.pk

    # Cleanup:
    migrator.reset()


@pytest.mark.django_db()
def test_0027_alter_file_status(migrator):
    # Not using test parametrisation to avoid repeatedly rerunning migration
    status_options = [
        ("uploaded", "processing"),
        ("parsing", "processing"),
        ("chunking", "processing"),
        ("embedding", "processing"),
        ("indexing", "processing"),
        ("unknown", "errored"),
        ("failed", "errored"),
        ("complete", "complete"),
        ("deleted", "deleted"),
        ("errored", "errored"),
        ("processing", "processing"),
    ]
    files = []

    old_state = migrator.apply_initial_migration(("redbox_core", "0026_alter_file_status"))

    original_file = SimpleUploadedFile("original_file.txt", b"Lorem Ipsum.")

    User = old_state.apps.get_model("redbox_core", "User")
    File = old_state.apps.get_model("redbox_core", "File")

    user = User.objects.create(email="someone@example.com")

    for status_option in status_options:
        files.append(
            File.objects.create(
                user=user,
                original_file=original_file,
                original_file_name=original_file.name,
                core_file_uuid=uuid4(),
                status=status_option[0],
            )
        )

    new_state = migrator.apply_tested_migration(
        ("redbox_core", "0027_alter_file_status"),
    )
    NewFile = new_state.apps.get_model("redbox_core", "File")  # noqa: N806

    for idx, file in enumerate(files):
        new_file = NewFile.objects.get(pk=file.pk)
        assert new_file.status == status_options[idx][1]

    # Cleanup:
    migrator.reset()


@pytest.mark.django_db()
def test_0029_user_ai_settings(migrator):
    old_state = migrator.apply_initial_migration(("redbox_core", "0028_aisettings"))

    User = old_state.apps.get_model("redbox_core", "User")
    User.objects.create(email="someone@example.com")

    new_state = migrator.apply_tested_migration(
        ("redbox_core", "0029_user_ai_settings"),
    )
    NewUser = new_state.apps.get_model("redbox_core", "User")  # noqa: N806

    for user in NewUser.objects.all():
        assert user.ai_settings.label == "default"
