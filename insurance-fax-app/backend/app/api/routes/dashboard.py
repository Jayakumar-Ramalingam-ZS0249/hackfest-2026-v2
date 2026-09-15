"""Dashboard statistics -- always computed from the real in-memory claim store, never fabricated."""

from fastapi import APIRouter

from ...repositories.claim_repository import claim_repository

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/statistics")
def get_dashboard_statistics():
    return claim_repository.statistics()
