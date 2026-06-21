from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from app.db.models import User, UserSession
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.get_by(email=email.lower().strip())

    def create_user(
        self,
        *,
        email: str,
        display_name: str,
        password_hash: str | None = None,
        auth_provider: str = "password",
        avatar_url: str | None = None,
    ) -> User:
        return self.create(
            email=email.lower().strip(),
            display_name=display_name.strip(),
            password_hash=password_hash,
            auth_provider=auth_provider,
            avatar_url=avatar_url,
        )

    def touch_last_login(self, user: User, at: datetime | None = None) -> User:
        return self.update(user, last_login_at=at or datetime.utcnow())


class UserSessionRepository(BaseRepository[UserSession]):
    model = UserSession

    def create_session(
        self,
        *,
        user_id,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> UserSession:
        return self.create(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    def get_active_by_token_hash(self, refresh_token_hash: str) -> UserSession | None:
        stmt = select(UserSession).where(
            UserSession.refresh_token_hash == refresh_token_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > func.now(),
        ).with_for_update()
        return self.session.execute(stmt).scalar_one_or_none()

    def revoke(self, session: UserSession, at: datetime | None = None) -> UserSession:
        return self.update(session, revoked_at=at or datetime.utcnow())
