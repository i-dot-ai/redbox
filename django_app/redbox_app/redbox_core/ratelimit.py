from datetime import UTC, datetime, timedelta
from uuid import UUID

from asgiref.sync import sync_to_async

from redbox.models.chain import RedboxState
from redbox.models.settings import get_settings
from redbox_app.redbox_core.models import ChatMessage, User

_settings = get_settings()


class UserRateLimiter:
    def __init__(self, token_ratelimit=_settings.user_token_ratelimit) -> None:
        self.token_ratelimit = token_ratelimit

    async def is_allowed(self, state: RedboxState):
        consumed_ratelimit = await sync_to_async(self.get_tokens_for_user_in_last_minute)(state.user_uuid)
        request_tokens = self.calculate_request_credits(state)
        return request_tokens < self.token_ratelimit - consumed_ratelimit

    def get_tokens_for_user_in_last_minute(self, user_uuid: UUID):
        user = User.objects.get(pk=user_uuid)
        since = datetime.now(UTC) - timedelta(minutes=1)
        recent_messages = ChatMessage.get_since(user, since)
        return sum(m.token_count for m in recent_messages)

    def calculate_request_credits(self, state: RedboxState) -> int:
        return int(sum(d.metadata.get("token_count", 0) for d in state.documents))
