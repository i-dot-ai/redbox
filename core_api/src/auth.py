from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from starlette import status


http_bearer = HTTPBearer()


async def get_user_uuid(token: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)]) -> UUID:
    """this extracts the user_uuid for Authorization only,
    no Authentication is attempted."""
    try:
        payload = jwt.get_unverified_claims(token.credentials)
        return UUID(payload["user_uuid"])
    except (TypeError, ValueError, KeyError, JWTError):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        raise credentials_exception
