import uuid

from redbox_app.redbox_core import models


class FileStatus():
    id: uuid
    status: models.ProcessingStatusEnum
