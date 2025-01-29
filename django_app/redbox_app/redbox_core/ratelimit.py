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
        consumed_ratelimit = await self.get_tokens_for_user_in_last_minute(state.user_uuid)
        request_tokens = self.calculate_request_credits(state)
        return request_tokens < self.token_ratelimit - consumed_ratelimit

    async def get_tokens_for_user_in_last_minute(self, user_uuid: UUID):
        user = await sync_to_async(User.objects.get)(pk=user_uuid)
        recent_messages = await sync_to_async(lambda u, d: list(ChatMessage.get_since(u, d)))(
            user, datetime.now(UTC) - timedelta(minutes=1)
        )
        return sum([m.token_count for m in recent_messages])

    def calculate_request_credits(self, state: RedboxState):
        return int(sum([d.metadata.get("token_count", 0) for d in state.documents]))
