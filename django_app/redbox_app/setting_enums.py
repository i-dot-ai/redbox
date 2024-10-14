import os
from enum import StrEnum

ADDITIONAL_HOSTS = os.environ.get("ADDITIONAL_HOSTS", "").split(";")
LOCAL_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]  # noqa: S104: Not in prod
LOCAL_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]


class Environment(StrEnum):
    def __new__(cls, value: str, is_test: bool, hosts=list[str]):
        obj = str.__new__(cls, [value])
        obj._value_ = value
        obj.is_test = is_test
        obj.hosts = hosts
        return obj

    @property
    def is_local(self) -> bool:
        return self is Environment.LOCAL

    @property
    def uses_minio(self) -> bool:
        return self.is_test

    LOCAL = ("LOCAL", True, [*LOCAL_HOSTS, *ADDITIONAL_HOSTS])  # nosec: B104: Not in prod
    INTEGRATION = ("INTEGRATION", True, [*LOCAL_HOSTS, *ADDITIONAL_HOSTS])  # nosec: B104: Not in prod
    DEV = ("DEV", False, ["redbox-dev.ai.cabinetoffice.gov.uk", *ADDITIONAL_HOSTS])
    PREPROD = ("PREPROD", False, ["redbox-preprod.ai.cabinetoffice.gov.uk", *ADDITIONAL_HOSTS])
    PROD = ("PROD", False, ["redbox.ai.cabinetoffice.gov.uk", *ADDITIONAL_HOSTS])


class Classification(StrEnum):
    """Security classifications
    https://www.gov.uk/government/publications/government-security-classifications/"""

    OFFICIAL = "Official"
    OFFICIAL_SENSITIVE = "Official Sensitive"
    SECRET = "Secret"  # noqa: S105
    TOP_SECRET = "Top Secret"  # noqa: S105
