"""Auth dependencies for protected routes."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from utils.config import get_settings

security = HTTPBearer(auto_error=False)


class AuthUser(BaseModel):
    """Authenticated user from JWT claims."""

    id: str  # sub claim - auth.users id
    email: str | None = None
    role: str = "authenticated"


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser:
    """Require a valid Supabase JWT. Verifies locally using JWT secret. Bypassed when auth_enabled=False."""
    settings = get_settings()
    if not settings.auth_enabled:
        return AuthUser(
            id="3dcc239c-78b3-46b3-afef-56e39647fff2",
            email="dev@local",
            role="authenticated",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth not configured. Set SUPABASE_JWT_SECRET in .env",
        )

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            audience="authenticated",
            algorithms=["HS256"],
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthUser(
        id=payload.get("sub", ""),
        email=payload.get("email"),
        role=payload.get("role", "authenticated"),
    )


async def optional_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser | None:
    """Return AuthUser if authenticated, None otherwise. Does not raise on missing/invalid token."""
    settings = get_settings()
    if not settings.auth_enabled:
        return AuthUser(id="3dcc239c-78b3-46b3-afef-56e39647fff2", email="dev@local", role="authenticated")
    if credentials is None or not credentials.credentials or not credentials.credentials.strip():
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret or "",
            audience="authenticated",
            algorithms=["HS256"],
        )
        return AuthUser(
            id=payload.get("sub", ""),
            email=payload.get("email"),
            role=payload.get("role", "authenticated"),
        )
    except (jwt.PyJWTError, TypeError):
        return None
