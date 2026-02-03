import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.authz import require_admin_or_ingest, require_user_or_admin_key

router = APIRouter(prefix="/news", tags=["news"])


@router.post("", response_model=schemas.NewsRead, status_code=201)
def create_news(
    payload: schemas.NewsCreate,
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin_or_ingest),
):
    source = None
    if payload.source_id is not None:
        source = db.query(models.Source).filter(models.Source.id == payload.source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="source not found")
    elif payload.source_identifier:
        source = (
            db.query(models.Source)
            .filter(
                models.Source.platform == payload.platform,
                models.Source.identifier == payload.source_identifier,
            )
            .first()
        )
        if not source:
            source = models.Source(
                name=payload.source_name or payload.source_identifier,
                platform=payload.platform,
                identifier=payload.source_identifier,
                is_active=True,
            )
            db.add(source)
            db.flush()

    if source and not source.is_active:
        return Response(status_code=204)

    source_name = payload.source_name or (source.name if source else None)
    if not source_name:
        raise HTTPException(
            status_code=422, detail="source_name is required when no source is resolved"
        )

    content_hash = payload.content_hash
    if not content_hash:
        content_hash = hashlib.sha256(payload.content.strip().encode("utf-8")).hexdigest()

    # Insert into staging table for smart processing
    # Messages will be moved to archive after successful interval summary
    news = models.NewsFeedStaging(
        source_id=source.id if source else None,
        source_name=source_name,
        platform=payload.platform,
        source_message_id=payload.source_message_id,
        author_name=payload.author_name,
        content=payload.content,
        clean_content=payload.clean_content,
        content_hash=content_hash,
        timestamp=payload.timestamp,
        importance_score=payload.importance_score,
        category=payload.category,
        is_news_related=True,  # Will be updated by smart filtering during summarization
    )
    db.add(news)
    db.commit()
    db.refresh(news)
    return news


@router.get("", response_model=list[schemas.NewsRead])
def list_news(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    platform: schemas.Platform | None = None,
    category: str | None = None,
    min_score: int | None = Query(None, ge=1, le=10),
    source_id: int | None = None,
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_user_or_admin_key),
):
    """
    List recent news from the staging table (real-time feed).
    Messages appear here immediately when received.
    """
    query = db.query(models.NewsFeedStaging)
    if active_only:
        query = query.join(
            models.Source, 
            models.NewsFeedStaging.source_id == models.Source.id,
            isouter=True
        ).filter(
            (models.Source.is_active.is_(True)) | (models.NewsFeedStaging.source_id.is_(None))
        )
    if platform is not None:
        query = query.filter(models.NewsFeedStaging.platform == platform)
    if category:
        query = query.filter(models.NewsFeedStaging.category == category)
    if min_score is not None:
        query = query.filter(models.NewsFeedStaging.importance_score >= min_score)
    if source_id is not None:
        query = query.filter(models.NewsFeedStaging.source_id == source_id)

    return (
        query.order_by(models.NewsFeedStaging.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/archive", response_model=list[schemas.NewsRead])
def list_archived_news(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    platform: schemas.Platform | None = None,
    category: str | None = None,
    min_score: int | None = Query(None, ge=1, le=10),
    source_id: int | None = None,
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_user_or_admin_key),
):
    """
    List archived news (after summarization).
    Use this for historical search and older messages.
    """
    query = db.query(models.NewsArchive)
    if platform is not None:
        query = query.filter(models.NewsArchive.platform == platform)
    if category:
        query = query.filter(models.NewsArchive.category == category)
    if min_score is not None:
        query = query.filter(models.NewsArchive.importance_score >= min_score)
    if source_id is not None:
        query = query.filter(models.NewsArchive.source_id == source_id)

    return (
        query.order_by(models.NewsArchive.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/stats")
def news_stats(
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_user_or_admin_key),
):
    base = db.query(models.NewsArchive)
    if active_only:
        base = base.join(models.Source).filter(models.Source.is_active.is_(True))

    total = base.count()
    latest = base.with_entities(func.max(models.NewsArchive.timestamp)).scalar()

    platform_rows = (
        base.with_entities(
            models.NewsArchive.platform.label("platform"),
            func.count(models.NewsArchive.id).label("count"),
        )
        .group_by(models.NewsArchive.platform)
        .all()
    )
    by_platform = [
        {"platform": str(row.platform), "count": int(row.count or 0)}
        for row in platform_rows
    ]

    source_query = db.query(
        models.NewsArchive.source_id,
        models.NewsArchive.source_name,
        models.NewsArchive.platform,
        func.count(models.NewsArchive.id).label("count"),
        models.Source.is_active,
    ).outerjoin(models.Source, models.NewsArchive.source_id == models.Source.id)
    if active_only:
        source_query = source_query.filter(models.Source.is_active.is_(True))

    source_rows = (
        source_query.group_by(
            models.NewsArchive.source_id,
            models.NewsArchive.source_name,
            models.NewsArchive.platform,
            models.Source.is_active,
        )
        .order_by(func.count(models.NewsArchive.id).desc())
        .all()
    )
    by_source = [
        {
            "source_id": int(row.source_id) if row.source_id is not None else None,
            "source_name": row.source_name,
            "platform": str(row.platform),
            "count": int(row.count or 0),
            "is_active": bool(row.is_active) if row.is_active is not None else None,
        }
        for row in source_rows
    ]

    return {
        "total": int(total or 0),
        "latest_timestamp": latest.isoformat() if latest else None,
        "by_platform": by_platform,
        "by_source": by_source,
    }
