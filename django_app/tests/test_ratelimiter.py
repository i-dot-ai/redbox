from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from langchain_core.documents import Document

from redbox.models.chain import RedboxState
from redbox_app.redbox_core.ratelimit import UserRateLimiter

test_user_uuid = uuid4()


@dataclass
class UserActivity:
    total_document_tokens: int
    number_documents: int


def request_state(number_of_documents: int, total_document_tokens: int):
    return RedboxState(
        user_uuid=test_user_uuid,
        documents=[
            Document("", metadata={"token_count": int(total_document_tokens / number_of_documents)})
            for _ in range(number_of_documents)
        ],
    )


@pytest.mark.parametrize(
    ("token_ratelimit", "users_consumed_tokens", "request_state", "expect_allowed"),
    [
        (1000, {test_user_uuid: 100}, request_state(2, 200), True),
        (1000, {test_user_uuid: 100, uuid4(): 1000, uuid4(): 900}, request_state(1, 800), True),
        (1000, {test_user_uuid: 800}, request_state(2, 240), False),
        (1000, {test_user_uuid: 800}, request_state(8, 400), False),
    ],
)
def test_ratelimiter(
    token_ratelimit: int, users_consumed_tokens: dict[UUID, int], request_state: RedboxState, expect_allowed: bool
):
    ratelimiter = UserRateLimiter(token_ratelimit=token_ratelimit)

    def create_user_tokens_consumed_mock(tokens_per_user: dict[UUID, int]):
        def _impl(user_uuid: UUID):
            return tokens_per_user.get(user_uuid, 0)

        return _impl

    ratelimiter.get_tokens_for_user_in_last_minute = create_user_tokens_consumed_mock(users_consumed_tokens)
    request_allowed = ratelimiter.is_allowed(request_state)
    if request_allowed != expect_allowed:
        pytest.fail(
            reason=f"Request allow status did not match: Expected [{expect_allowed}]. Received [{request_allowed}]"
        )
