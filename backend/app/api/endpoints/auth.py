from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status

from app.api.auth import CurrentUser
from app.api.deps import RepositoryDep
from app.core.config import settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expires_at,
    verify_password,
)
from app.db.models import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserRead


router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_COOKIE_NAME = "refresh_token"


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.app_env != "development",
        samesite="lax",
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.app_env != "development",
        samesite="lax",
        path="/api/v1/auth",
    )


def issue_tokens(
    *,
    user: User,
    request: Request,
    response: Response,
    repositories: RepositoryDep,
) -> dict[str, object]:
    refresh_token = create_refresh_token()
    repositories.user_sessions.create_session(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        expires_at=refresh_token_expires_at(),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    access_token, expires_in = create_access_token(user.id)
    set_refresh_cookie(response, refresh_token)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": user,
    }


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    repositories: RepositoryDep,
):
    if repositories.users.get_by_email(payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    user = repositories.users.create_user(
        email=payload.email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
    )
    return user


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    repositories: RepositoryDep,
):
    user = repositories.users.get_by_email(payload.email)
    encoded_hash = user.password_hash if user and user.password_hash else DUMMY_PASSWORD_HASH
    password_matches = verify_password(payload.password, encoded_hash)
    if user is None or user.password_hash is None or not password_matches:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    repositories.users.touch_last_login(user, datetime.now(UTC))
    return issue_tokens(user=user, request=request, response=response, repositories=repositories)


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    request: Request,
    response: Response,
    repositories: RepositoryDep,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    if refresh_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing")
    session = repositories.user_sessions.get_active_by_token_hash(hash_refresh_token(refresh_token))
    if session is None:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid or expired")
    user = repositories.users.get(session.user_id)
    if user is None:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    repositories.user_sessions.revoke(session, datetime.now(UTC))
    return issue_tokens(user=user, request=request, response=response, repositories=repositories)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    repositories: RepositoryDep,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> Response:
    if refresh_token is not None:
        session = repositories.user_sessions.get_active_by_token_hash(hash_refresh_token(refresh_token))
        if session is not None:
            repositories.user_sessions.revoke(session, datetime.now(UTC))
    clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUser):
    return current_user
