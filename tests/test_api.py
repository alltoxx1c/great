import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Link, User


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app, follow_redirects=False) as c:
        yield c


def auth(c, name="alice"):
    c.post("/auth/register", json={"username": name, "password": "password123"})
    r = c.post("/auth/token", data={"username": name, "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_flow(client):
    h = auth(client)
    r = client.post("/links", json={"original_url": "https://example.com/a", "max_clicks": 2}, headers=h)
    assert r.status_code == 201
    link = r.json()
    # дедупликация
    r2 = client.post("/links", json={"original_url": "https://example.com/a"}, headers=h)
    assert r2.status_code == 200 and r2.json()["code"] == link["code"]

    for _ in range(2):
        r = client.get(f"/{link['code']}")
        assert r.status_code == 302 and r.headers["location"] == "https://example.com/a"
    assert client.get(f"/{link['code']}").status_code == 419   # лимит кликов
    assert client.get("/links", headers=h).json()[0]["clicks"] == 2

    assert client.get("/not-a-uuid").status_code == 404
    assert client.get("/00000000-0000-4000-8000-000000000000").status_code == 404


def test_limits_and_delete(client):
    h = auth(client)
    ids = []
    for i in range(3):
        ids.append(client.post("/links", json={"original_url": f"https://e.com/{i}"}, headers=h).json()["id"])
    assert client.post("/links", json={"original_url": "https://e.com/x"}, headers=h).status_code == 403

    # soft delete освобождает слот; повторный DELETE и чужой -> 404
    assert client.delete(f"/links/{ids[0]}", headers=h).status_code == 204
    assert client.delete(f"/links/{ids[0]}", headers=h).status_code == 404
    assert client.post("/links", json={"original_url": "https://e.com/x"}, headers=h).status_code == 201
    h2 = auth(client, "bob")
    assert client.delete(f"/links/{ids[1]}", headers=h2).status_code == 404

    # premium = 5
    with SessionLocal() as db:
        db.execute(update(User).where(User.username == "alice").values(role="premium"))
        db.commit()
    assert client.post("/links", json={"original_url": "https://e.com/y"}, headers=h).status_code == 201
    assert client.post("/links", json={"original_url": "https://e.com/z"}, headers=h).status_code == 201
    assert client.post("/links", json={"original_url": "https://e.com/w"}, headers=h).status_code == 403


def test_deleted_404_and_expired_419(client):
    h = auth(client)
    a = client.post("/links", json={"original_url": "https://e.com/1"}, headers=h).json()
    b = client.post("/links", json={"original_url": "https://e.com/2"}, headers=h).json()
    client.delete(f"/links/{a['id']}", headers=h)
    assert client.get(f"/{a['code']}").status_code == 404
    with SessionLocal() as db:
        db.execute(update(Link).where(Link.id == b["id"]).values(expires_at=datetime(2000, 1, 1)))
        db.commit()
    assert client.get(f"/{b['code']}").status_code == 419


def test_auth_required(client):
    assert client.get("/links").status_code == 401
    assert client.post("/auth/token", data={"username": "x", "password": "y"}).status_code == 401
