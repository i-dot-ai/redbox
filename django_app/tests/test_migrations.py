


def test_0073_chatmessage_new_source_files(original_file, migrator):
    old_state = migrator.apply_initial_migration(("redbox_core", "0072_delete_activityevent"))

    User = old_state.apps.get_model("redbox_core", "User")
    user = User.objects.create(email="someone@example.com")

    ChatLLMBackend = old_state.apps.get_model("redbox_core", "ChatLLMBackend")
    chat_backend = ChatLLMBackend.objects.first()

    Chat = old_state.apps.get_model("redbox_core", "Chat")
    chat = Chat.objects.create(name="my-chat", user=user, chat_backend=chat_backend)

    ChatMessage = old_state.apps.get_model("redbox_core", "ChatMessage")
    chat_message = ChatMessage.objects.create(chat=chat)

    File = old_state.apps.get_model("redbox_core", "File")
    file = File.objects.create(
        user=user,
        original_file=original_file,
        original_file_name=original_file.name,
    )

    Citation = old_state.apps.get_model("redbox_core", "Citation")
    citation = Citation(chat_message=chat_message, file=file, source="USER UPLOADED DOCUMENT", text="hello!")
    citation.save()

    new_state = migrator.apply_tested_migration(
        ("redbox_core", "0073_chatmessage_new_source_files"),
    )

    NewChatMessage = new_state.apps.get_model("redbox_core", "ChatMessage")  # noqa: N806
    new_chat_message = NewChatMessage.objects.get(id=chat_message.id)
    assert new_chat_message.source_files.count() == 1
    assert new_chat_message.source_files.first().id == file.id
