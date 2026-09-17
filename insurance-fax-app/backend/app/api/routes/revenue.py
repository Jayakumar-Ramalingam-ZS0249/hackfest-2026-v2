"""Revenue opportunity endpoint -- pure math, never touches an LLM."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...agents.revenue_engine import calculate_revenue

router = APIRouter(tags=["revenue"])


class RevenueRequest(BaseModel):
    touchpoints: int = Field(..., ge=0)
    agent_count: int = Field(..., ge=0)
    domain: str = Field("general")


@router.post("/revenue/calculate")
def calculate(payload: RevenueRequest):
    return calculate_revenue(touchpoints=payload.touchpoints, agent_count=payload.agent_count, domain=payload.domain)
