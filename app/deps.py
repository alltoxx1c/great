from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Link, User
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    exc = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Invalid credentials", headers={"WWW-Authenticate": "Bearer"}
    )
    username = decode_token(token)
    if not username:
        raise exc
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        raise exc
    return user


def own_link(
    link_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Link:
    """Своя и не удалённая ссылка; чужая/несуществующая -> 404 (не раскрываем существование)."""
    link = db.scalar(
        select(Link).where(Link.id == link_id, Link.user_id == user.id, Link.deleted_at.is_(None))
    )
    if not link:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found")
    return link
