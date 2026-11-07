from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import LINK_LIMITS
from ..database import get_db
from ..deps import get_current_user, own_link
from ..models import Link, User, utcnow
from ..schemas import LinkCreate, LinkOut

router = APIRouter(prefix="/links", tags=["links"])


@router.post("", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
def create_link(
    data: LinkCreate,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    url = str(data.original_url)
    now = utcnow()
    active = (Link.user_id == user.id) & Link.active_clause(now)

    # дедупликация: активная ссылка на тот же URL -> вернуть существующую
    existing = db.scalar(select(Link).where(active, Link.original_url == url))
    if existing:
        response.status_code = status.HTTP_200_OK
        return existing

    # лимит активных ссылок по роли
    limit = LINK_LIMITS.get(user.role, LINK_LIMITS["user"])
    count = db.scalar(select(func.count()).select_from(Link).where(active))
    if count >= limit:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Active links limit reached ({limit})")

    link = Link(user_id=user.id, original_url=url, expires_at=data.expires_at, max_clicks=data.max_clicks)
    db.add(link)
    db.commit()
    return link


@router.get("", response_model=list[LinkOut])
def list_links(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Свои не удалённые ссылки (включая истёкшие — их видно с is_active=false)."""
    return db.scalars(
        select(Link).where(Link.user_id == user.id, Link.deleted_at.is_(None)).order_by(Link.id)
    ).all()


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(link: Link = Depends(own_link), db: Session = Depends(get_db)):
    link.deleted_at = utcnow()
    db.add(link)
    db.commit()
