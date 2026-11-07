import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Link, utcnow

router = APIRouter(tags=["redirect"])

PAGE_EXPIRED = 419  # нестандартный код по заданию (по HTTP корректнее 410 Gone)


@router.get("/{code}")
def follow(code: str, db: Session = Depends(get_db)):
    try:
        code = str(uuid.UUID(code))
    except ValueError:
        raise HTTPException(404, "Link not found")

    link = db.scalar(select(Link).where(Link.code == code, Link.deleted_at.is_(None)))
    if not link:
        raise HTTPException(404, "Link not found")

    # Атомарно: проверка активности и инкремент в одном UPDATE.
    # Два параллельных запроса не смогут превысить max_clicks.
    result = db.execute(
        update(Link).where(Link.id == link.id, Link.active_clause(utcnow())).values(clicks=Link.clicks + 1),
        execution_options={"synchronize_session": False},  # проверка целиком на стороне БД
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(PAGE_EXPIRED, "Link expired")

    return RedirectResponse(link.original_url, status_code=302)
