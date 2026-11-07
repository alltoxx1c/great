import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, and_, or_
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    """SQLite отдаёт naive datetime — считаем их UTC."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user", server_default="user")  # user | premium
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    links: Mapped[list["Link"]] = relationship(back_populates="user")


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    original_url: Mapped[str] = mapped_column(String(2048))
    code: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicks: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="links")

    # ---- единственное место, где определено, что такое «активная» ссылка ----
    @staticmethod
    def active_clause(now: datetime | None = None):
        """SQL-фильтр: не удалена, не истекла, лимит кликов не исчерпан."""
        now = now or utcnow()
        return and_(
            Link.deleted_at.is_(None),
            or_(Link.expires_at.is_(None), Link.expires_at > now),
            or_(Link.max_clicks.is_(None), Link.clicks < Link.max_clicks),
        )

    @property
    def is_expired(self) -> bool:
        if self.expires_at is not None and as_utc(self.expires_at) <= utcnow():
            return True
        return self.max_clicks is not None and self.clicks >= self.max_clicks

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None and not self.is_expired
