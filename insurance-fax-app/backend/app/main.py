"""
Fax / Claim Intake API
========================

FastAPI backend for the AI-assisted insurance claim intake tool.

RUN LOCALLY:
    cd backend
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000

Then open the Angular app (see /frontend), which is already configured
to call http://localhost:8000.

Architecture: this file only builds the FastAPI app and wires up
routers/middleware/exception handlers. Request handling lives in
app/api/routes/*, business logic in app/services/*, and orchestration
of the multi-stage document pipeline in app/agents/orchestrator.py.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.router import api_router
from .core.config import get_settings
from .core.exceptions import register_exception_handlers
from .core.logging import configure_logging

settings = get_settings()
configure_logging(settings.app_env)

app = FastAPI(title="Insurance Claim Intake API", version="0.2.0")

# CORS: wide open for local development so the Angular dev server
# (usually http://localhost:4200) can call this API freely. Lock this
# down to your real frontend origin before deploying to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "aiProvider": settings.ai_provider if settings.ai_configured else "rule_based (no AI_API_KEY configured)",
    }
