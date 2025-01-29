
from datetime import datetime, UTC
from functools import cache, lru_cache
from uuid import UUID
from pydantic import BaseModel, Field

from redbox.models.chain import RedboxState
from redbox.models.settings import get_settings

class UserRateLimitRecord(BaseModel):
    credits: int = Field(default=get_settings().user_token_rate_limit_second*60)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def update_credits(self, max_credits=get_settings().user_token_rate_limit_second*60):
        seconds_since_last = min(60, (datetime.now(UTC) - self.last_updated).seconds)
        self.credits = int(min(
            self.credits + get_settings().user_token_rate_limit_second*seconds_since_last,
            max_credits
        ))


class UserRateLimiter():

    def __init__(
            self,
            initial_user_credits = 350_000
    ) -> None:
        self.initial_user_credits = initial_user_credits

    def is_allowed(self, state: RedboxState):
        user_uuid = state.user_uuid
        user_ratelimit_record = self.get_record(user_uuid)
        request_credits = self.calculate_request_credits(state)
        print(f"Request {request_credits}/{user_ratelimit_record.credits} credits")
        if request_credits < user_ratelimit_record.credits:
            print(f"Request allowed: {request_credits}/{user_ratelimit_record.credits}")
            user_ratelimit_record.credits -= request_credits
            return True
        else:
            return False
        
    def get_record(self, user_uuid: UUID) -> UserRateLimitRecord:
        record = self._get_cached_record(user_uuid)
        record.update_credits(max_credits=self.initial_user_credits)
        return record

    def calculate_request_credits(self, state: RedboxState):
        return int(sum([d.metadata.get("token_count", 0) for d in state.documents]))

    @lru_cache(get_settings().number_cached_ratelimit_records)
    def _get_cached_record(self, user_uuid: UUID):
        """
        Returns a new rate limit record for this user. As the function is cached/lru_cached an existing record for this
        user is returned if present
        """
        return UserRateLimitRecord(credits=self.initial_user_credits)
        