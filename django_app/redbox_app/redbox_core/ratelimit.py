from datetime import UTC, datetime, timedelta
from uuid import UUID

from redbox.models.chain import RedboxState
from redbox.models.settings import get_settings
from redbox_app.redbox_core.models import ChatMessage, User

_settings = get_settings()


class UserRateLimiter:
    def __init__(self, token_ratelimit=_settings.user_token_ratelimit) -> None:
        self.token_ratelimit = token_ratelimit

    def is_allowed(self, state: RedboxState):
        consumed_ratelimit = self.get_tokens_for_user_in_last_minute(state.user_uuid)
        request_tokens = self.calculate_request_credits(state)
        return request_tokens < self.token_ratelimit - consumed_ratelimit

    def get_tokens_for_user_in_last_minute(self, user_uuid: UUID):
        recent_messages = ChatMessage.get_since(User.objects.get(user_uuid), datetime.now(UTC) - timedelta(minutes=1))
        return sum([m.token_count for m in recent_messages])

    def calculate_request_credits(self, state: RedboxState):
        return int(sum([d.metadata.get("token_count", 0) for d in state.documents]))
