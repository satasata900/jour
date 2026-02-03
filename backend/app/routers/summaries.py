from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models, schemas
from app.database import get_db
from app.authz import require_admin, require_user_or_admin_key

router = APIRouter(prefix="/summaries", tags=["summaries"])


@router.get("/stats")
def summary_stats(
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_user_or_admin_key),
):
    """
    Get counts for all summary period types directly from database.
    Returns: {interval: N, daily: N, weekly: N, monthly: N}
    """
    counts = (
        db.query(
            models.Summary.period_type,
            func.count(models.Summary.id).label("count")
        )
        .group_by(models.Summary.period_type)
        .all()
    )
    
    # Build response with all types (default to 0)
    result = {
        "interval": 0,
        "daily": 0,
        "weekly": 0,
        "monthly": 0
    }
    
    for period_type, count in counts:
        if period_type in result:
            result[period_type] = count
    
    return result


@router.get("", response_model=list[schemas.SummaryRead])
def list_summaries(
    period_type: schemas.SummaryPeriod | None = None,
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_user_or_admin_key),
):
    query = db.query(models.Summary)
    if period_type is not None:
        query = query.filter(models.Summary.period_type == period_type)
    return (
        query.order_by(models.Summary.period_start.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.patch("/{summary_id}", response_model=schemas.SummaryRead)
def update_summary(
    summary_id: int,
    payload: schemas.SummaryUpdate,
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin),
):
    summary = db.query(models.Summary).filter(models.Summary.id == summary_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found.")
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Summary content cannot be empty.")
    summary.content = content
    summary.is_locked = True
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary
