# Technical Architecture — Zuci Agent Services
### Agentic Prescriptive Analytics Hackfest Showcase

All technology named below is verified against the actual repository (`frontend/package.json`, `backend/requirements.txt`, source files cited inline). No technology is assumed.

---

## 1. Verified Technology Stack

| Layer | Technology (verified) | Notes |
|---|---|---|
| Frontend | Angular 17.3, TypeScript, SCSS | Standalone components, no NgModules, lazy-loaded routes |
| Backend | FastAPI (Python), `uvicorn` | `main.py` app factory + CORS + exception handlers |
| AI provider | Google Gemini via `google-generativeai` SDK | Model configurable (`AI_MODEL`, default `gemini-flash-latest`) |
| Document parsing | PyMuPDF, `pdfplumber` | Native text + table extraction |
| OCR | Tesseract (via a Python wrapper), triggered per-page | Only runs when native/table text on a page is under 20 characters |
| Text-to-speech | `pyttsx3` (offline OS engine: SAPI5 / NSSpeechSynthesizer / espeak) | AI Claim Manager voice output |
| Speech-to-text | Browser-native `SpeechRecognition` / `webkitSpeechRecognition` | No backend involvement |
| Database | **None** — in-memory Python dictionaries | `claim_repository`, `discovery_repository`, `chat_repository`, `upload_job_repository` |
| Validation | Pydantic v2 | Request schemas + domain checks |
| Auth | Frontend-only mock (`localStorage`) | No backend authentication exists |

**Explicitly not present, and not shown in any diagram:** Node.js, PostgreSQL/MySQL/any SQL database, Azure OpenAI, OpenAI (non-Google), Redis, Celery/RQ, Docker/Kubernetes manifests, any ML framework (scikit-learn/PyTorch/TensorFlow), any optimization solver (MIP/CBC/OR-Tools).

---

## 2. Layered Architecture

```text
Frontend (Angular 17)
    |  HttpClient, JSON over HTTP
    v
API Layer (FastAPI -- 10 route modules, e.g. faxes, claims, chat, discovery,
           implementation, roi, revenue, governance, dashboard, health)
    |  thin routers: Pydantic validation, immediate delegation
    v
Orchestration (agents/orchestrator.py :: run_pipeline())
    |
    v
Decision Layer
    +-- Prediction/Signal:  DocumentRelevanceService (deterministic match score)
    |                       ClaimExtractionService (Gemini or RuleBasedProvider)
    +-- Rules:              core/config.py thresholds
    |                       (invalid_match_threshold=25, review_match_threshold=60,
    |                        low_confidence_threshold=0.70)
    +-- Policy:             agents/discovery.py AGENT_WHITELIST (domain-scoped)
    +-- Optimization:       roi/calculate, revenue/calculate (fixed formulas)  [PARTIAL]
    +-- AI Agent:           4 bounded Gemini calls behind one AIProvider abstraction
    |                       (ClaimExtractionService, ChatService, discovery.py, implementation.py)
    v
Action Layer (claim status transition; /api/faxes/{id}/decision; human "Approve & Resolve")
    v
Outcome / KPI (analytics_service.py -> Governance & Managed Operations pages)
    v
Feedback / Learning  [PROPOSED -- no implementation found]
```

---

## 3. The AI Provider Abstraction (the actual guardrail seam)

`services/ai/base.py` defines an abstract `AIProvider`. Two concrete implementations exist:

- `GeminiProvider` — real calls to Google Gemini, forced JSON-mode on every call.
- `RuleBasedProvider` — zero-dependency deterministic fallback (regex extraction, keyword-based Discovery assessment, templated Implementation output).

`services/ai/factory.py` selects and caches a provider instance per `(provider, model, key-suffix)`. Every one of the four AI touch points below calls through this same abstraction — there is exactly **one** code path to an external LLM in the whole application:

| AI touch point | File | Deterministic guardrail applied immediately after |
|---|---|---|
| Claim field extraction | `services/extraction/claim_extraction_service.py` | Source-text must literally appear in the document; cross-page conflict check |
| Grounded chat | `services/chat/chat_service.py` | Cited `sourceText` must appear in the exact context sent, or the answer is discarded |
| Discovery assessment | `agents/discovery.py` | Recommended agents filtered against a domain whitelist; rejects logged |
| Implementation simulation | `agents/implementation.py` | Skip AI below 60% confidence; force-flag missing diagnosis; force review if no patient name |

---

## 4. Data Architecture

| Store | Technology | Contents | Persists? |
|---|---|---|---|
| ClaimRepository | Python dict, in-memory | Claim records + audit log | No |
| DiscoveryRepository | Python dict, in-memory | Stored process assessments | No |
| ChatRepository | Python dict, in-memory | AI Claim Manager conversation history | No |
| UploadJobRepository | Python dict, in-memory | Async upload job progress | No |
| `.env` | Flat file, git-ignored | AI provider/model/key, the three thresholds, upload size limit | Yes (file, not app state) |

No real database exists. The repository-pattern seam (`repositories/*.py`) is the designed path for a future database swap — the seam exists; the database behind it does not.

---

## 5. Security Posture (stated plainly, not glossed over)

| Control | Status |
|---|---|
| PDF upload validation (extension, content-type, size) | [IMPLEMENTED] |
| Consistent typed-error → JSON contract | [IMPLEMENTED] |
| Logging excludes raw document text/field values | [IMPLEMENTED] |
| Frontend route guards (`authGuard`/`guestGuard`) | [IMPLEMENTED] — client-side only |
| Backend authentication on any API endpoint | [PROPOSED] — none exists |
| RBAC / multi-role permissions | [PROPOSED] — one mock role (`Clinical Admin`) exists |
| CORS restricted to a real origin | [PROPOSED] — currently `allow_origins=["*"]` |
| Rate limiting on AI-backed endpoints | [PROPOSED] |
| Tamper-evident audit log | [PROPOSED] — currently a plain in-memory list |

---

## 6. Why This Architecture Supports (But Does Not Yet Contain) Optimization and Learning

- **Optimization:** the Implementation agent already assembles exactly the context a solver would need (claim fields, confidence, recommended agents). Adding a constrained-optimization step (e.g., ranking the `attentionRequired` queue by value × urgency under a fixed reviewer-capacity constraint) is additive — it does not require restructuring the existing pipeline.
- **Learning:** every manager correction already flows through `POST /api/faxes/{id}/decision` and is persisted on the claim record. The missing piece is a consumer of that correction stream that feeds back into threshold tuning or model prompts — the data exists; the feedback loop does not.
