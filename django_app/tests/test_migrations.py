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
def test_0028_aisettings(migrator):
    old_state = migrator.apply_initial_migration(("redbox_core", "0027_alter_file_status"))

    User = old_state.apps.get_model("redbox_core", "User")
    User.objects.create(email="someone@example.com")

    new_state = migrator.apply_tested_migration(
        ("redbox_core", "0028_aisettings"),
    )
    NewUser = new_state.apps.get_model("redbox_core", "User")  # noqa: N806

    for user in NewUser.objects.all():
        assert user.ai_settings.label == "default"


@pytest.mark.django_db()
def test_0029_rename_chathistory_chat_alter_chat_options(migrator):
    old_state = migrator.apply_initial_migration(("redbox_core", "0028_aisettings"))

    User = old_state.apps.get_model("redbox_core", "User")
    user = User.objects.create(email="someone@example.com")

    ChatHistory = old_state.apps.get_model("redbox_core", "ChatHistory")
    chat_history = ChatHistory.objects.create(name="my-chat", users=user)

    ChatMessage = old_state.apps.get_model("redbox_core", "ChatMessage")
    ChatMessage.objects.create(chat_history=chat_history)

    new_state = migrator.apply_tested_migration(
        ("redbox_core", "0029_rename_chathistory_chat_alter_chat_options"),
    )
    Chat = new_state.apps.get_model("redbox_core", "Chat")
    chat = Chat.objects.get(pk=chat_history.pk)

    assert chat.chatmessage_set.count() == 1


@pytest.mark.django_db()
def test_0030_chatmessagerating_chips(migrator):
    old_state = migrator.apply_initial_migration(("redbox_core", "0029_rename_chathistory_chat_alter_chat_options"))

    User = old_state.apps.get_model("redbox_core", "User")
    user = User.objects.create(email="someone@example.com")

    Chat = old_state.apps.get_model("redbox_core", "Chat")
    chat = Chat.objects.create(users=user, name="my-chat")

    ChatMessage = old_state.apps.get_model("redbox_core", "ChatMessage")
    chat_message = ChatMessage.objects.create(chat=chat)

    ChatMessageRating = old_state.apps.get_model("redbox_core", "ChatMessageRating")
    chat_message_rating = ChatMessageRating.objects.create(chat_message=chat_message, rating=3, text="very average")

    ChatMessageRatingChip = old_state.apps.get_model("redbox_core", "ChatMessageRatingChip")
    ChatMessageRatingChip.objects.create(rating=chat_message_rating, text="apple")
    ChatMessageRatingChip.objects.create(rating=chat_message_rating, text="pear")

    new_state = migrator.apply_tested_migration(
        ("redbox_core", "0030_chatmessagerating_chips"),
    )
    NewChatMessageRating = new_state.apps.get_model("redbox_core", "ChatMessageRating")  # noqa: N806
    new_chat_message_rating = NewChatMessageRating.objects.get(pk=chat_message_rating.pk)
    assert new_chat_message_rating.chips == ["apple", "pear"]


@pytest.mark.django_db()
def test_0031_chatmessage_rating_chatmessage_rating_chips_and_more(migrator):
    old_state = migrator.apply_initial_migration(("redbox_core", "0030_chatmessagerating_chips"))

    User = old_state.apps.get_model("redbox_core", "User")
    user = User.objects.create(email="someone@example.com")

    Chat = old_state.apps.get_model("redbox_core", "Chat")
    chat = Chat.objects.create(users=user, name="my-chat")

    ChatMessage = old_state.apps.get_model("redbox_core", "ChatMessage")
    chat_message = ChatMessage.objects.create(chat=chat)

    ChatMessageRating = old_state.apps.get_model("redbox_core", "ChatMessageRating")
    ChatMessageRating.objects.create(chat_message=chat_message, rating=3, text="very average", chips=["apple", "pear"])

    new_state = migrator.apply_tested_migration(
        ("redbox_core", "0031_chatmessage_rating_chatmessage_rating_chips_and_more"),
    )
    NewChatMessage = new_state.apps.get_model("redbox_core", "ChatMessage")  # noqa: N806
    new_chat_message = NewChatMessage.objects.get(pk=chat_message.pk)
    assert new_chat_message.rating_chips == ["apple", "pear"]
    assert new_chat_message.rating == 3
    assert new_chat_message.rating_text == "very average"


@pytest.mark.django_db()
def test_0032_user_new_business_unit(migrator):
    old_state = migrator.apply_initial_migration(
        ("redbox_core", "0031_chatmessage_rating_chatmessage_rating_chips_and_more")
    )

    BusinessUnit = old_state.apps.get_model("redbox_core", "BusinessUnit")
    pm_office = BusinessUnit.objects.get(name="Prime Minister's Office")

    User = old_state.apps.get_model("redbox_core", "User")
    user = User.objects.create(email="someone@example.com", business_unit=pm_office)

    new_state = migrator.apply_tested_migration(
        ("redbox_core", "0032_user_new_business_unit"),
    )
    NewUser = new_state.apps.get_model("redbox_core", "User")  # noqa: N806
    user = NewUser.objects.get(pk=user.pk)
    assert user.business_unit == "Prime Minister's Office"


@pytest.mark.django_db()
def test_0042_chat_chat_backend_chat_chat_map_question_prompt_and_more(migrator):
    old_state = migrator.apply_initial_migration(("redbox_core", "0041_alter_aisettings_chat_backend"))

    User = old_state.apps.get_model("redbox_core", "User")
    user = User.objects.create(email="someone@example.com")

    Chat = old_state.apps.get_model("redbox_core", "Chat")
    chat = Chat.objects.create(name="my chat", user=user)

    ai_settings_fields = [
        "max_document_tokens",
        "context_window_size",
        "llm_max_tokens",
        "rag_k",
        "rag_num_candidates",
        "rag_desired_chunk_size",
        "elbow_filter_enabled",
        "chat_system_prompt",
        "chat_question_prompt",
        "stuff_chunk_context_ratio",
        "chat_with_docs_system_prompt",
        "chat_with_docs_question_prompt",
        "chat_with_docs_reduce_system_prompt",
        "retrieval_system_prompt",
        "retrieval_question_prompt",
        "condense_system_prompt",
        "condense_question_prompt",
        "map_max_concurrency",
        "chat_map_system_prompt",
        "chat_map_question_prompt",
        "reduce_system_prompt",
        "match_boost",
        "knn_boost",
        "similarity_threshold",
        "chat_backend",
    ]

    for field in ai_settings_fields:
        assert not hasattr(chat, field)

    new_state = migrator.apply_tested_migration(
        ("redbox_core", "0042_chat_chat_backend_chat_chat_map_question_prompt_and_more"),
    )

    new_chat_model = new_state.apps.get_model("redbox_core", "Chat")
    new_chat = new_chat_model.objects.get(id=chat.id)

    for field in ai_settings_fields:
        assert getattr(new_chat, field) == getattr(chat.user.ai_settings, field)
        assert getattr(new_chat, field) is not None
