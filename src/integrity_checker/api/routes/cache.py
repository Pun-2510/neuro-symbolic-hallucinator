"""Cache management routes (admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from integrity_checker.api.deps import get_db, require_admin
from integrity_checker.db.models import User
from integrity_checker.db.repository import Repository

router = APIRouter()


class CacheStatsResponse(BaseModel):
    total: int
    by_source: dict
    total_hits: int
    avg_hit_count: float


class CacheClearResponse(BaseModel):
    deleted_count: int


@router.get("/stats", response_model=CacheStatsResponse)
def get_cache_stats(admin: User = Depends(require_admin), db=Depends(get_db)):
    """Get citation cache statistics (admin only)."""
    repo = Repository(db)
    stats = repo.get_cache_stats()
    return CacheStatsResponse(**stats)


@router.delete("", response_model=CacheClearResponse)
def clear_cache(admin: User = Depends(require_admin), db=Depends(get_db)):
    """Clear all citation cache (admin only)."""
    repo = Repository(db)
    deleted_count = repo.clear_cache()
    repo.commit()
    return CacheClearResponse(deleted_count=deleted_count)
