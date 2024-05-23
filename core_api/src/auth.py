import logging
from http import HTTPStatus
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from starlette import status
from starlette.requests import Request
from starlette.websockets import WebSocket

log = logging.getLogger()

http_bearer = HTTPBearer()


async def get_user_uuid(token: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)]) -> UUID:
    """this extracts the user_uuid for Authorization only,
    no Authentication is attempted."""
    try:
        payload = jwt.get_unverified_claims(token.credentials)
        return UUID(payload["user_uuid"])
    except (TypeError, ValueError, KeyError, JWTError) as e:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        raise credentials_exception from e


class JWTAuth(HTTPBearer):
    async def __call__(self, request: Request = None, websocket: WebSocket = None) -> Optional[UUID]:
        request = request or websocket
        if not request:
            if self.auto_error:
                raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Not authenticated")
            return None
        token = await super().__call__(request)
        return await get_user_uuid_from_bearer_token(token)


async def get_user_uuid_from_bearer_token(token):
    try:
        payload = jwt.get_unverified_claims(token.credentials)
        return UUID(payload["user_uuid"])
    except (TypeError, ValueError, KeyError, JWTError) as e:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        raise credentials_exception from e
