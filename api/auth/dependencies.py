"""Auth dependencies for protected routes."""
import asyncio
import json
import urllib.request
from urllib.error import HTTPError, URLError

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


def _verify_via_supabase_auth(token: str, url: str, anon_key: str) -> AuthUser | None:
    """Verify JWT by calling Supabase Auth server. Works with both legacy and asymmetric signing keys."""
    req = urllib.request.Request(
        f"{url.rstrip('/')}/auth/v1/user",
        headers={
            "apikey": anon_key,
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            user = data.get("id") or data.get("sub")
            email = data.get("email")
            if user:
                return AuthUser(id=str(user), email=email, role="authenticated")
    except (HTTPError, URLError, json.JSONDecodeError, KeyError):
        pass
    return None


def _verify_via_jwt_secret(token: str, secret: str) -> AuthUser | None:
    """Verify JWT locally using legacy HS256 secret. Fails if project uses asymmetric keys."""
    try:
        payload = jwt.decode(
            token,
            secret,
            audience="authenticated",
            algorithms=["HS256"],
        )
        return AuthUser(
            id=payload.get("sub", ""),
            email=payload.get("email"),
            role=payload.get("role", "authenticated"),
        )
    except jwt.PyJWTError:
        return None


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser:
    """Require a valid Supabase JWT. Verifies via Auth server (preferred) or JWT secret. Bypassed when auth_enabled=False."""
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

    # Prefer Supabase Auth server verification (works with legacy + asymmetric signing keys)
    if settings.supabase_url and settings.supabase_publishable_key:
        user = await asyncio.to_thread(
            _verify_via_supabase_auth,
            token,
            settings.supabase_url,
            settings.supabase_publishable_key,
        )
        if user:
            return user

    # Fallback to local JWT secret (legacy HS256 only)
    if settings.supabase_jwt_secret:
        user = _verify_via_jwt_secret(token, settings.supabase_jwt_secret)
        if user:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
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
    token = credentials.credentials
    if settings.supabase_url and settings.supabase_publishable_key:
        user = await asyncio.to_thread(
            _verify_via_supabase_auth,
            token,
            settings.supabase_url,
            settings.supabase_publishable_key,
        )
        if user:
            return user
    if settings.supabase_jwt_secret:
        user = _verify_via_jwt_secret(token, settings.supabase_jwt_secret)
        if user:
            return user
    return None
