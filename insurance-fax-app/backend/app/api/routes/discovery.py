"""Discovery assessment endpoints -- classifies a process description and
recommends an agent architecture for it. Never re-implements OCR/extraction;
this is a separate, upstream "what should we automate" analysis."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...agents.discovery import run_discovery
from ...core.config import get_settings
from ...core.exceptions import NotFoundError
from ...repositories.discovery_repository import discovery_repository
from ...services.ai.factory import get_ai_provider

router = APIRouter(tags=["discovery"])


class DiscoveryRequest(BaseModel):
    process_text: str = Field(..., description="Pasted or uploaded process description")


@router.post("/discovery/assess")
def assess_process(payload: DiscoveryRequest):
    settings = get_settings()
    ai_provider = get_ai_provider(settings)
    result = run_discovery(payload.process_text, ai_provider)
    return discovery_repository.add(result)


@router.get("/discovery/{assessment_id}")
def get_assessment(assessment_id: str):
    assessment = discovery_repository.get(assessment_id)
    if assessment is None:
        raise NotFoundError(f"Assessment '{assessment_id}' was not found.")
    return assessment
