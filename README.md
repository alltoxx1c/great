# URL shortener (FastAPI)

    pip install -r requirements.txt
    export DATABASE_URL=sqlite:///./app.db SECRET_KEY=$(openssl rand -hex 32)
    alembic upgrade head
    uvicorn app.main:app --reload
    pytest

Premium выдаётся прямо в БД: `UPDATE users SET role='premium' WHERE username='...'`.
