"""ROI (Business Impact) endpoint -- pure math, never touches an LLM."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...agents.roi_engine import calculate_roi

router = APIRouter(tags=["roi"])


class RoiRequest(BaseModel):
    annual_volume: int = Field(..., ge=0)
    mins_per_request: float = Field(..., ge=0)
    automation_pct: float = Field(..., ge=0, le=1)
    cost_per_hour: float = Field(25, ge=0)


@router.post("/roi/calculate")
def calculate(payload: RoiRequest):
    return calculate_roi(
        annual_volume=payload.annual_volume,
        mins_per_request=payload.mins_per_request,
        automation_pct=payload.automation_pct,
        cost_per_hour=payload.cost_per_hour,
    )
