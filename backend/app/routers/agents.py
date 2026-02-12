import json
import logging
import os
import re
from string import Formatter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_user_id_for_token
from app.authz import get_current_user, require_admin, require_user_or_admin_key

AGENTS_BASE_URL = os.getenv("AGENTS_BASE_URL", "http://agents:8001").rstrip("/")

router = APIRouter()
logger = logging.getLogger("agents")

REQUIRED_FIELDS = {
    "router": {"task", "context", "format_instructions"},
    "monitor": {"window", "stats"},
    "editor": {"task", "content"},
    "search": {"task"},
    "general": {"task", "context"},
    "custom": {"task"},
}
KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
TITLE_MAX_CHARS = 60
TITLE_ROUTE = os.getenv("CHAT_TITLE_ROUTE", "general").strip().lower() or "general"


class AgentRunRequest(BaseModel):
    task: str = Field(..., min_length=1)
    context: str | None = None
    route: str | None = None
    window_hours: int | None = Field(default=24, ge=1, le=168)
    max_items: int | None = Field(default=50, ge=1, le=200)


def _normalize_key(value: str) -> str:
    key = value.strip().lower()
    if not KEY_PATTERN.match(key):
        raise HTTPException(
            status_code=400,
            detail="Agent key must be 3-64 chars (lowercase letters, numbers, - or _).",
        )
    return key


def _extract_fields(template: str) -> set[str]:
    fields = set()
    for _, field_name, _, _ in Formatter().parse(template):
        if field_name:
            fields.add(field_name)
    return fields


def _validate_template(agent_type: str, template: str) -> None:
    required = REQUIRED_FIELDS.get(agent_type, set())
    if not required:
        return
    fields = _extract_fields(template)
    missing = sorted(required - fields)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Template missing required fields: {', '.join(missing)}",
        )


def _call_agents(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    url = f"{AGENTS_BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=180) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else str(exc)
        raise HTTPException(status_code=502, detail=f"Agent service error: {body}") from exc
    except URLError as exc:
        raise HTTPException(
            status_code=502, detail=f"Agent service unavailable: {exc.reason}"
        ) from exc

    if not body:
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"raw": body}


def _get_user_id_from_header(authorization: str | None) -> int | None:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    return get_user_id_for_token(token)


def _clean_chat_title(value: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", value).strip()
    cleaned = cleaned.strip('"').strip("'").strip()
    cleaned = re.sub(r"^(?:title|عنوان)\s*[:\-]\s*", "", cleaned, flags=re.IGNORECASE)
    if not cleaned:
        return None
    if len(cleaned) > TITLE_MAX_CHARS:
        cleaned = cleaned[:TITLE_MAX_CHARS].rstrip()
    return cleaned


def _generate_chat_title(user_message: str, assistant_message: str) -> str | None:
    task = (
        "Create a short Arabic title (3-6 words) for this conversation. "
        "Return title only, no quotes or punctuation."
    )
    context = f"User: {user_message}\nAssistant: {assistant_message}"
    payload = {"task": task, "context": context, "route": TITLE_ROUTE}
    response = _call_agents("POST", "/agents/run", payload=payload)
    if isinstance(response, dict):
        output = response.get("output")
    else:
        output = None
    if not isinstance(output, str):
        return None
    return _clean_chat_title(output)


@router.get("/agents", response_model=list[schemas.AgentProfileRead])
def list_agents(
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_user_or_admin_key),
) -> list[models.AgentProfile]:
    return (
        db.query(models.AgentProfile)
        .order_by(models.AgentProfile.is_system.desc(), models.AgentProfile.id.asc())
        .all()
    )


@router.get("/agents/health")
def agents_health(
    _access: models.User | None = Depends(require_admin),
) -> Any:
    return _call_agents("GET", "/health")


@router.get("/agents/{agent_id}", response_model=schemas.AgentProfileRead)
def get_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_user_or_admin_key),
) -> models.AgentProfile:
    agent = db.query(models.AgentProfile).filter(models.AgentProfile.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return agent


@router.post("/agents", response_model=schemas.AgentProfileRead, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: schemas.AgentProfileCreate,
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin),
) -> models.AgentProfile:
    data = payload.model_dump(mode="json")
    data["key"] = _normalize_key(data["key"])
    agent_type = data["agent_type"]

    _validate_template(agent_type, data["user_prompt"])

    exists = (
        db.query(models.AgentProfile)
        .filter(models.AgentProfile.key == data["key"])
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Agent key already exists.")

    agent = models.AgentProfile(**data)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.patch("/agents/{agent_id}", response_model=schemas.AgentProfileRead)
def update_agent(
    agent_id: int,
    payload: schemas.AgentProfileUpdate,
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin),
) -> models.AgentProfile:
    agent = db.query(models.AgentProfile).filter(models.AgentProfile.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")

    updates = payload.model_dump(exclude_unset=True, mode="json")

    if "key" in updates:
        updates["key"] = _normalize_key(updates["key"])

    new_key = updates.get("key")
    if new_key and new_key != agent.key:
        exists = (
            db.query(models.AgentProfile)
            .filter(models.AgentProfile.key == new_key)
            .first()
        )
        if exists:
            raise HTTPException(status_code=400, detail="Agent key already exists.")

    if "agent_type" in updates:
        template = updates.get("user_prompt", agent.user_prompt)
        _validate_template(updates["agent_type"], template)
    elif "user_prompt" in updates:
        _validate_template(agent.agent_type, updates["user_prompt"])

    for field, value in updates.items():
        setattr(agent, field, value)

    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin),
) -> None:
    agent = db.query(models.AgentProfile).filter(models.AgentProfile.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    db.delete(agent)
    db.commit()


@router.post("/agents/run")
def agents_run(
    payload: AgentRunRequest,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(require_user_or_admin_key),
    x_gemini_key: str | None = Header(default=None, alias="X-Gemini-Key"),
    x_openrouter_key: str | None = Header(default=None, alias="X-OpenRouter-Key"),
    x_groq_key: str | None = Header(default=None, alias="X-Groq-Key"),
) -> Any:
    data = payload.model_dump(exclude_none=True)
    if x_gemini_key:
        data["gemini_api_key"] = x_gemini_key.strip()
    if x_openrouter_key:
        data["openrouter_api_key"] = x_openrouter_key.strip()
    if x_groq_key:
        data["groq_api_key"] = x_groq_key.strip()
    response = _call_agents("POST", "/agents/run", payload=data)
    if user and isinstance(response, dict):
        output = response.get("output")
        if isinstance(output, str) and output.strip():
            try:
                db.add(
                    models.ChatHistory(
                        user_id=user.id,
                        message=payload.task,
                        response=output,
                    )
                )
                db.commit()
            except Exception as exc:
                db.rollback()
                logger.warning("Failed to persist chat history: %s", exc)
    return response


# --- Chat History Endpoints ---

@router.get("/chat/sessions")
def get_chat_sessions(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """List user's chat sessions."""
    sessions = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == user.id)
        .order_by(models.ChatSession.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return sessions


@router.post("/chat/sessions", response_model=schemas.ChatSessionRead)
def create_chat_session(
    payload: schemas.NewChatSession,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Start a new chat session."""
    session = models.ChatSession(
        user_id=user.id,
        title=payload.title or "New Chat",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/chat/sessions/{session_id}", response_model=schemas.ChatSessionDetail)
def get_chat_session_details(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Get messages for a specific session."""
    session = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.delete("/chat/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    session = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/chat/sessions/{session_id}/messages", response_model=schemas.ChatMessageRead)
def add_chat_message(
    session_id: int,
    payload: schemas.ChatMessageCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Add a message to a session (history logging)."""
    session = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    message = models.ChatMessage(
        session_id=session.id,
        role=payload.role,
        content=payload.content,
    )
    db.add(message)
    
    # Update session updated_at
    session.updated_at = func.now()
    db.commit()
    db.refresh(message)
    if payload.role in {"model", "assistant"} and (
        session.title is None or session.title == "New Chat"
    ):
        try:
            user_message = (
                db.query(models.ChatMessage)
                .filter(
                    models.ChatMessage.session_id == session.id,
                    models.ChatMessage.role == "user",
                )
                .order_by(models.ChatMessage.created_at.desc())
                .first()
            )
            if user_message and user_message.content and payload.content:
                title = _generate_chat_title(user_message.content, payload.content)
                if title:
                    session.title = title
                    db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("Failed to generate chat title: %s", exc)
    return message
