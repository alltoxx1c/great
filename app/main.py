from fastapi import FastAPI

from .routers import auth, links, redirect

app = FastAPI(title="URL shortener")
app.include_router(auth.router)
app.include_router(links.router)
app.include_router(redirect.router)  # последним: /{code} ловит всё остальное
