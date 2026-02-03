import logging
import logging
from pathlib import Path

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.agent_seeds import seed_agents
from app.auth_seeds import seed_test_user
from app.database import SessionLocal
from app.routers import agents, auth, news, notifications, settings, sources, summaries, users
from app.summary_service import start_summary_worker, stop_summary_worker
from app.telegram_bot import start_telegram_bot_worker, stop_telegram_bot_worker

app = FastAPI()
logger = logging.getLogger("backend")

REQUIRE_HTTPS = os.getenv("REQUIRE_HTTPS", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


@app.middleware("http")
async def enforce_https(request: Request, call_next):
    if not REQUIRE_HTTPS:
        return await call_next(request)
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    if proto != "https":
        return JSONResponse(
            status_code=400, content={"detail": "HTTPS is required."}
        )
    return await call_next(request)

app.include_router(sources.router)
app.include_router(news.router)
app.include_router(summaries.router)
app.include_router(agents.router)
app.include_router(settings.router)
app.include_router(notifications.router)
app.include_router(auth.router)
app.include_router(users.router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup_tasks() -> None:
    start_summary_worker(app)
    start_telegram_bot_worker(app)
    with SessionLocal() as db:
        try:
            seed_agents(db)
        except Exception as exc:
            logger.warning("Agent seed failed: %s", exc)
        try:
            seed_test_user(db)
        except Exception as exc:
            logger.warning("User seed failed: %s", exc)


@app.on_event("shutdown")
def shutdown_tasks() -> None:
    stop_summary_worker(app)
    stop_telegram_bot_worker(app)


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard")
def dashboard_index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/dashboard/{path:path}")
def dashboard_sections(path: str):
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}
