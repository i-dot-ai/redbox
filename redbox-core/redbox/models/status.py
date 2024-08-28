from pydantic import BaseModel


class StatusResponse(BaseModel):
    status: str
    uptime_seconds: float
    version: str
