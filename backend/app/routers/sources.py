from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.authz import require_admin_or_ingest

router = APIRouter(prefix="/sources", tags=["sources"])


def _normalize_rss_url(value: str) -> str:
    url = value.strip()
    if not url:
        raise HTTPException(status_code=400, detail="RSS URL is required.")
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
        parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="RSS URL must be a valid http(s) URL.")
    return url


@router.post("", response_model=schemas.SourceRead, status_code=201)
def create_source(
    payload: schemas.SourceCreate,
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin_or_ingest),
):
    if payload.platform == schemas.Platform.rss:
        payload.identifier = _normalize_rss_url(payload.identifier)
    existing = (
        db.query(models.Source)
        .filter(
            models.Source.platform == payload.platform,
            models.Source.identifier == payload.identifier,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="source already exists")

    source = models.Source(
        name=payload.name,
        platform=payload.platform,
        identifier=payload.identifier,
        is_active=payload.is_active,
        schedule_interval_minutes=payload.schedule_interval_minutes,
        config=payload.config,
        labels=payload.labels,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("", response_model=list[schemas.SourceRead])
def list_sources(
    is_active: bool | None = None,
    platform: schemas.Platform | None = None,
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin_or_ingest),
):
    query = db.query(models.Source)
    if is_active is not None:
        query = query.filter(models.Source.is_active == is_active)
    if platform is not None:
        query = query.filter(models.Source.platform == platform)
    return query.order_by(models.Source.created_at.desc()).all()


@router.patch("/{source_id}", response_model=schemas.SourceRead)
def update_source(
    source_id: int,
    payload: schemas.SourceUpdate,
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin_or_ingest),
):
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="source not found")

    data = payload.model_dump(exclude_unset=True)
    if "labels" in data and data["labels"] is None:
        data["labels"] = []
    for field, value in data.items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin_or_ingest),
) -> None:
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="source not found")
    db.delete(source)
    db.commit()
