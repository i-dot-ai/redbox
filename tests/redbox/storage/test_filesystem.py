def test_read_item(example_chuck_saved, file_system_storage_handler):
    obj = file_system_storage_handler.read_item(
        example_chuck_saved.uuid, example_chuck_saved.__class__.__name__
    )
    assert obj == example_chuck_saved


def test_read_items(
    example_chuck_saved, example_chuck_unsaved, file_system_storage_handler
):
    objs = file_system_storage_handler.read_items(
        [example_chuck_saved.uuid, example_chuck_unsaved.uuid],
        example_chuck_saved.__class__.__name__,
    )
    assert objs == [example_chuck_saved]


def test_list_all_items(
    example_chuck_saved, example_chuck_unsaved, file_system_storage_handler
):
    objs = file_system_storage_handler.list_all_items(
        example_chuck_saved.__class__.__name__
    )
    assert objs == [example_chuck_saved.uuid]
