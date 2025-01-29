from dataclasses import dataclass
from uuid import uuid3, uuid4

import pytest
from langchain_core.documents import Document

from redbox.models.chain import RedboxState
from redbox_app.redbox_core.ratelimit import UserRateLimiter

test_run_uuid = uuid4()


@dataclass
class UserActivity:
    total_document_tokens: int
    number_documents: int
    number_of_requests: int = 1


def generate_user_activity(state_definitions: list[UserActivity]):
    """
    Creates a list of RedboxStates representing a user request based on the definitions passed in.
    There will be a state for each request with the total document tokens split evenly across
    each users requests
    """
    all_user_requests = [
        [
            RedboxState(
                user_uuid=uuid3(test_run_uuid, str(i)),
                documents=[
                    Document("", metadata={"token_count": int(s.total_document_tokens / s.number_documents)})
                    for n in range(s.number_documents)
                ],
            )
            for i in range(s.number_of_requests)
        ]
        for s in state_definitions
    ]
    return [i for internal_list in all_user_requests for i in internal_list]


@pytest.mark.parametrize(
    ("initial_user_credits", "user_activity_states", "ratelimit_should_be_triggered"),
    [
        (1000, generate_user_activity([UserActivity(2000, 2)]), True),
        (1000, generate_user_activity([UserActivity(100, 8), UserActivity(2000, 2)]), True),
        (
            1000,
            generate_user_activity(
                [
                    UserActivity(100, 8),
                    UserActivity(200, 4),
                ]
            ),
            False,
        ),
    ],
)
def test_ratelimiter(
    initial_user_credits: int, user_activity_states: list[RedboxState], ratelimit_should_be_triggered: bool
):
    ratelimiter = UserRateLimiter(initial_user_credits=initial_user_credits)
    for i, user_activity_state in enumerate(user_activity_states):
        if not ratelimiter.is_allowed(user_activity_state):
            if not ratelimit_should_be_triggered:
                pytest.fail(
                    reason=f"Ratelimit was unexpectedly triggered by user request [{i}] - \
                        {user_activity_state.model_dump()}"
                )
            break
    else:
        if ratelimit_should_be_triggered:
            pytest.fail(reason=f"All {len(user_activity_states)} requests allowed. Ratelimit was not triggered")
