"""FastAPI application entry point. Run with:

    uvicorn app.main:app --reload --port 8000

Interactive API docs are then available at http://localhost:8000/docs
"""

import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app import config, store
from app.agent import pipeline
from app.models.schemas import (
    AIRecommendation,
    Applicant,
    DashboardSummary,
    DecisionRequest,
    ToolCallRecord,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Claims Copilot API",
    description=(
        "Agentic Prescriptive Analytics demo backend for health insurance claims review. "
        "The AI layer only orchestrates and explains; every verification, fraud check, "
        "compliance check, and dollar amount is computed by plain Python business logic."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _not_found(applicant_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Applicant '{applicant_id}' not found")


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "claude_configured": bool(config.ANTHROPIC_API_KEY), "model": config.CLAUDE_MODEL}


@app.get("/api/applications", response_model=List[Applicant], tags=["applications"])
def get_applications(
    status: Optional[str] = Query(None, description="Filter by claim status"),
    sort_by: Optional[str] = Query(None, description="Field to sort by, e.g. risk_score, claim_amount_requested"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
) -> List[Applicant]:
    return store.list_applicants(status=status, sort_by=sort_by, order=order)


@app.get("/api/applications/{applicant_id}", response_model=Applicant, tags=["applications"])
def get_application(applicant_id: str) -> Applicant:
    applicant = store.get_applicant(applicant_id)
    if applicant is None:
        raise _not_found(applicant_id)
    return applicant


@app.post("/api/applications/{applicant_id}/ai-review", response_model=AIRecommendation, tags=["applications"])
def post_ai_review(applicant_id: str) -> AIRecommendation:
    if store.get_applicant(applicant_id) is None:
        raise _not_found(applicant_id)
    try:
        return pipeline.run_ai_review(applicant_id)
    except Exception as exc:  # last-resort guard: never let this crash the API
        logger.exception("AI review pipeline raised for %s", applicant_id)
        raise HTTPException(status_code=502, detail=f"AI review is temporarily unavailable: {exc}") from exc


@app.post("/api/applications/{applicant_id}/decision", response_model=Applicant, tags=["applications"])
def post_decision(applicant_id: str, body: DecisionRequest) -> Applicant:
    if store.get_applicant(applicant_id) is None:
        raise _not_found(applicant_id)
    return store.apply_decision(
        applicant_id=applicant_id,
        decision=body.decision,
        decided_by=body.decided_by,
        notes=body.notes,
        override_amount=body.override_amount,
    )


@app.get("/api/audit-log", response_model=List[ToolCallRecord], tags=["audit"])
def get_audit_log(
    applicant_id: Optional[str] = Query(None, description="Filter to a single applicant"),
) -> List[ToolCallRecord]:
    return store.list_audit(applicant_id=applicant_id)


@app.get("/api/dashboard/summary", response_model=DashboardSummary, tags=["dashboard"])
def get_dashboard_summary() -> DashboardSummary:
    return store.dashboard_summary()
