"""Agent-simulation endpoint -- runs a Discovery-recommended agent team
against an already-processed claim. Reuses the SAME claim record that
/api/faxes/upload's orchestrator.run_pipeline() already produced; never
re-runs OCR/extraction."""

from fastapi import APIRouter
from pydantic import BaseModel

from ...agents.implementation import run_agent_simulation
from ...core.config import get_settings
from ...core.exceptions import NotFoundError
from ...repositories.claim_repository import claim_repository
from ...repositories.discovery_repository import discovery_repository
from ...services.ai.factory import get_ai_provider

router = APIRouter(tags=["simulation"])


class SimulationRequest(BaseModel):
    fax_id: str
    assessment_id: str


@router.post("/implementation/simulate")
def simulate(payload: SimulationRequest):
    fax_record = claim_repository.get(payload.fax_id)  # raises NotFoundError (404) if missing

    assessment = discovery_repository.get(payload.assessment_id)
    if assessment is None:
        raise NotFoundError(f"Assessment '{payload.assessment_id}' was not found.")

    settings = get_settings()
    ai_provider = get_ai_provider(settings)
    result = run_agent_simulation(fax_record, assessment["recommended_agents"], ai_provider)
    result["fax_id"] = payload.fax_id
    result["assessment_id"] = payload.assessment_id
    return result
