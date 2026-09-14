"""
Fax Intake API
================

FastAPI backend for the AI-assisted fax intake tool. This is the
"functional application" backend -- it actually runs the pipeline
described in the LLD and stores results in memory so the Angular
frontend has real data to render.

RUN LOCALLY:
    cd backend
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000

Then open the Angular app (see /frontend/README section) which is
already configured to call http://localhost:8000.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import time

from .agents.orchestrator import run_pipeline

app = FastAPI(title="Fax Intake API", version="0.1.0")

# CORS: wide open for local development so the Angular dev server
# (usually http://localhost:4200) can call this API freely. Lock this
# down to your real frontend origin before deploying to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores. Swap these for a real database (Postgres, etc.)
# before going to production -- this MVP keeps everything in RAM so
# it resets whenever the server restarts.
FAXES: dict = {}
AUDIT_LOG: list = []


class DecisionPayload(BaseModel):
    approved: bool
    corrections: Optional[dict] = None  # { field_name: corrected_value }
    reviewer: str = "unknown_user"


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/faxes/upload")
async def upload_fax(file: UploadFile = File(...)):
    """
    Accepts a fax PDF, runs the full extraction/eligibility/confidence
    pipeline, stores the result, and returns it to the caller so the
    UI can render the patient info form immediately.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported in this MVP.")

    pdf_bytes = await file.read()
    record = run_pipeline(pdf_bytes, file.filename)
    FAXES[record["id"]] = record

    AUDIT_LOG.append({
        "fax_id": record["id"],
        "action": "pipeline_run",
        "timestamp": record["received_at"],
        "detail": f"Extraction pipeline ran with {record['overall_confidence']}% overall confidence",
    })

    return record


@app.get("/api/faxes")
def list_faxes():
    """Returns a lightweight summary list for the Fax Intake queue view."""
    return [
        {
            "id": f["id"],
            "filename": f["filename"],
            "received_at": f["received_at"],
            "status": f["status"],
            "overall_confidence": f["overall_confidence"],
            "needs_review_count": f["needs_review_count"],
        }
        for f in FAXES.values()
    ]


@app.get("/api/faxes/{fax_id}")
def get_fax(fax_id: str):
    record = FAXES.get(fax_id)
    if not record:
        raise HTTPException(status_code=404, detail="Fax not found")
    return record


@app.post("/api/faxes/{fax_id}/decision")
def submit_decision(fax_id: str, payload: DecisionPayload):
    """
    Human-in-the-loop step. A reviewer either approves the fax as-is
    (moving it to Resolved) or submits corrections for any flagged
    fields, which get logged for future retraining -- exactly per the
    LLD's "Review / learning agent" and audit-trail requirements.
    """
    record = FAXES.get(fax_id)
    if not record:
        raise HTTPException(status_code=404, detail="Fax not found")

    if payload.corrections:
        for field_name, corrected_value in payload.corrections.items():
            if field_name in record["fields"]:
                original_value = record["fields"][field_name]["value"]
                record["fields"][field_name]["value"] = corrected_value
                record["fields"][field_name]["status"] = "auto_fill"  # now human-confirmed
                AUDIT_LOG.append({
                    "fax_id": fax_id,
                    "action": "field_corrected",
                    "field": field_name,
                    "original_value": original_value,
                    "corrected_value": corrected_value,
                    "reviewer": payload.reviewer,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                })

    record["status"] = "resolved" if payload.approved else "needs_review"
    record["needs_review_count"] = sum(
        1 for f in record["fields"].values() if f["status"] == "needs_review"
    )

    AUDIT_LOG.append({
        "fax_id": fax_id,
        "action": "decision_submitted",
        "approved": payload.approved,
        "reviewer": payload.reviewer,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })

    return record


@app.get("/api/faxes/{fax_id}/audit-log")
def get_audit_log(fax_id: str):
    return [entry for entry in AUDIT_LOG if entry.get("fax_id") == fax_id]
