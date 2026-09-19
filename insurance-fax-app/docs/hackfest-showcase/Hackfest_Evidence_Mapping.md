# Evidence Mapping — Claim → Repository → Status
### Every claim in the showcase documents traces to one of these rows. Nothing is asserted without a file/screen citation.

| Claim | Repository file / code | Screen | Status | Evidence |
|---|---|---|---|---|
| PDF upload with real per-stage progress | `backend/app/agents/orchestrator.py` (`run_pipeline`), `POST /api/faxes/upload-async` | Fax Intake | [IMPLEMENTED] | `_report()` calls at 5 real checkpoints (uploading, OCR/extracting, relevance, AI extraction, verifying, eligibility, finalizing) |
| OCR fallback | `backend/app/services/documents/pdf_service.py` | Fax Intake | [IMPLEMENTED] | Triggered per-page when native/table text < 20 characters |
| Document relevance / match score | `backend/app/services/documents/relevance_service.py` | Fax Intake, Governance | [IMPLEMENTED] | `DocumentRelevanceService.analyze()`, deterministic keyword-signal scoring 0-100 |
| Three configured policy thresholds | `backend/app/core/config.py` (lines 37, 38, 41) | Governance | [IMPLEMENTED] | `invalid_match_threshold=25`, `review_match_threshold=60`, `low_confidence_threshold=0.70` |
| AI field extraction | `backend/app/services/extraction/claim_extraction_service.py` | Fax Intake | [IMPLEMENTED] | Gemini JSON-mode call; `legacy_status` set from `low_confidence_threshold` comparison |
| Deterministic fallback extraction | `RuleBasedProvider` (`services/ai/rule_based_provider.py`) | Fax Intake | [IMPLEMENTED] | Used automatically when `ai_provider.name == "rule_based"` |
| Source-text grounding | `claim_extraction_service.py`; `chat_service.py` | Fax Intake ("View Source"), AI Claim Manager | [IMPLEMENTED] | Value/citation must literally appear in the document/context sent |
| Agent whitelist enforcement | `backend/app/agents/discovery.py` (`AGENT_WHITELIST`, lines 23-28) | Growth Studio → Discovery | [IMPLEMENTED] | `filtered_agents = [a for a in raw_agents if a in whitelist]`; rejects logged |
| Confidence-based simulation override | `backend/app/agents/implementation.py` (`LOW_CONFIDENCE_ESCALATION_THRESHOLD = 60`) | Growth Studio → Implementation | [IMPLEMENTED] | AI call skipped entirely below 60% confidence; missing-diagnosis/patient-name force overrides |
| Grounded AI chat | `backend/app/services/chat/chat_service.py` | AI Claim Manager (floating widget) | [IMPLEMENTED] | Ambiguity check + quick-action match run in code before any LLM call |
| Human approval gate | `POST /api/faxes/{id}/decision`; frontend "Approve & Resolve" | Fax Intake | [IMPLEMENTED] | Only path to `status: resolved` |
| Live KPIs | `backend/app/services/dashboard/analytics_service.py` (`build_overview`) | Governance, Managed Operations | [IMPLEMENTED] | `summary`, `financial`, `statusDistribution`, `quality`, `documentAnalytics`, `attentionRequired` — all computed from real claim data |
| Audit trail | `analytics_service.py` (`recentActivity`); in-memory audit log | Governance | [IMPLEMENTED] | Appended on every state-changing action; not tamper-evident (plain list) |
| Eligibility lookup | `backend/app/agents/eligibility.py`, `backend/app/mock_db.py` | Fax Intake (read-only fields) | [PARTIALLY IMPLEMENTED] | Logic is real; `ELIGIBILITY_DB = {}` is a hardcoded empty dict, so it always returns "Not Found" |
| ROI / Revenue calculators | `POST /api/roi/calculate`, `POST /api/revenue/calculate` | Growth Studio → Impact/Revenue | [IMPLEMENTED] (arithmetic only) | Fixed formulas over user-entered inputs — no comparison of alternative actions |
| True optimization (alternative-action selection) | — no file found | — | [PROPOSED] | No solver dependency in `requirements.txt`; no ranking/selection logic across candidate actions anywhere in the codebase |
| Trained prediction/ML model | — no file found | — | [PROPOSED] | No ML dependency (`scikit-learn`/`torch`/`tensorflow`) in `requirements.txt`; no trained model artifact in the repository |
| Feedback / learning loop | — no file found | — | [PROPOSED] | Corrections persist to the claim record (`decision_submitted` audit action) but are not consumed by any retraining or threshold-tuning process |
| Multi-role RBAC | `frontend/src/app/services/auth.service.ts` | Login | [PROPOSED] | Single hardcoded mock role (`Clinical Admin`); never checked against a permission table |
| Backend authentication | — no `/api/auth/*` route exists | — | [PROPOSED] | Every FastAPI endpoint is unauthenticated; `authGuard` is Angular-side only |
| CORS restricted to a real origin | `backend/app/main.py` | — | [PROPOSED] | `allow_origins=["*"]`, explicitly commented as a dev convenience |

**How to use this table live:** if a judge questions any claim in the showcase document or demo script, this table is the fallback source — cite the file, not the slide.
