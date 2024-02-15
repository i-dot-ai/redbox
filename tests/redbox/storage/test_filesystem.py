from uuid import uuid4


def test_read_item(saved_example_chuck, file_system_storage_handler):
    obj = file_system_storage_handler.read_item(
        saved_example_chuck.uuid, saved_example_chuck.__class__.__name__
    )
    assert obj == saved_example_chuck


def test_read_items(saved_example_chuck, file_system_storage_handler):
    objs = file_system_storage_handler.read_items(
        [saved_example_chuck.uuid, str(uuid4())], saved_example_chuck.__class__.__name__
    )
    assert objs == [saved_example_chuck]
