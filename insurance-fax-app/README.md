# Zuci Agent Services — AI-Assisted Insurance Claim Intake

> *Prediction tells us what is likely to happen. Our solution focuses on what should happen next.*

This app takes insurance claim documents from start to finish. You upload a
PDF (fax or claim form). The AI extracts the fields, and each value is checked
against the source text. Policy thresholds then route the claim, and a human
approves it before it is resolved. Every step is written to an audit log.

It also includes a **Legacy-to-Agent Transformation Factory**, which has five
stages:

1. Discovery
2. Architecture
3. Implementation
4. Governance
5. Managed Operations

Discovery through Implementation live in the Growth Studio, which also has ROI
and revenue calculators.

**Design rule: AI drafts, deterministic code decides.** Gemini proposes the
extracted fields and the assessments. Code-enforced thresholds, whitelists and
grounding checks decide what is accepted, what needs review and what escalates
to a person.

**Stack:** Angular 17 (frontend) · Python/FastAPI (backend) · Google Gemini (optional)

---

## Features

- **Document intake pipeline:**
  - **Text extraction:** PyMuPDF text, pdfplumber tables, and Tesseract OCR for each page that has no text layer.
  - **Classification:** the document type is detected (discharge summary, claim form, hospital bill, medical report, policy document) and scored for relevance. Low-match documents stop here, so no fields are made up.
  - **Field extraction:** Gemini, or regex as the fallback. Every value is checked against the source text. A value that can't be found in the source is marked `UNVERIFIED`, and values that disagree between pages are marked `CONFLICT`.
  - **Eligibility and confidence:** the member is looked up, each field gets a confidence score, and the claim is routed to `auto_filled` / `needs_review` / `invalid`.
  - **Progress:** async uploads report the real progress of each stage.
- **Fax Intake workbench:**
  - Queues: All, Needs Review, Queued, Resolved, Failed, Deleted.
  - Field editing with confidence highlighting.
  - Approve & Resolve.
  - Soft delete and restore.
  - An audit trail for each claim.
- **AI Claim Manager:**
  - A chat assistant grounded in the selected claim's documents. It uses "RAG-lite" and sends only the most relevant pages to the model.
  - If an answer isn't in the documents, it says so instead of guessing.
  - Voice input uses browser speech recognition.
  - Spoken replies come from offline TTS, with an animated avatar whose mouth follows the audio.
- **Growth Studio:**
  - Process discovery, which recommends agents from a code-enforced whitelist.
  - Architecture.
  - An implementation simulation that runs on real uploaded claims.
  - An ROI calculator and a revenue-opportunity calculator. Both are pure math, with no LLM.
- **Governance:**
  - The live routing thresholds.
  - The active AI provider.
- **Managed Operations:**
  - System health and throughput.
- **Dashboard analytics API:**
  - Overview with filters, an attention summary (drives the notification bell), and CSV export.

---

## Project structure

```
insurance-fax-app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, /api/health
│   │   ├── core/                # config (env vars), logging, exception handlers
│   │   ├── api/routes/          # documents, claims, chat, dashboard, tts,
│   │   │                        # discovery, simulation, roi, revenue, governance
│   │   ├── agents/              # orchestrator, eligibility, discovery,
│   │   │                        # implementation, roi_engine, revenue_engine
│   │   ├── services/
│   │   │   ├── ai/              # AIProvider interface, Gemini + rule-based providers
│   │   │   ├── documents/       # PDF/OCR extraction, relevance classification
│   │   │   ├── extraction/      # canonical field extraction + source verification
│   │   │   ├── chat/            # grounded claim assistant
│   │   │   ├── dashboard/       # analytics over the claim store
│   │   │   └── tts/             # offline text-to-speech (pyttsx3)
│   │   ├── repositories/        # in-memory stores (claims, chat, discovery, upload jobs)
│   │   ├── schemas/             # Pydantic models
│   │   └── mock_db.py           # eligibility lookup placeholder
│   ├── tests/                   # pytest suite
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/app/
│       ├── pages/               # landing, login, dashboard, claim-queue,
│       │                        # growth-studio, governance, managed-operations
│       ├── components/          # ai-manager, robot-speaking-avatar, transformation-funnel
│       ├── services/            # fax (API client), auth, voice, audio-playback
│       └── guards/              # auth / guest route guards
├── sample-documents/            # demo PDFs
└── docs/                        # showcase docs, architecture diagrams
```

---

## Prerequisites

- **Python 3.10 or newer.** The app has been developed on 3.12.
- **Node.js 18 or newer**, with npm.
- **Tesseract OCR** (optional). You only need it for scanned PDFs that have no
  text layer. Install the Tesseract binary and put it on your `PATH`. Without
  it, OCR is skipped.
- **A Google Gemini API key** (optional). Without a key, the backend uses
  regex-based extraction, and the chat assistant is turned off.

---

## Getting started

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # then set AI_API_KEY (optional)
uvicorn app.main:app --reload --port 8000
```

- The API docs (Swagger UI) are at <http://localhost:8000/docs>.
- To check that the backend is up, open <http://localhost:8000/api/health>.
  The response also shows which AI provider is active.

> `requirements.txt` includes `pywin32`, which only installs on Windows. On
> macOS or Linux, remove that line before you install. For TTS, Linux also
> needs `espeak`.

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

Open <http://localhost:4200>. The frontend calls the backend at
`http://localhost:8000/api`. That address is set in
[`frontend/src/app/services/fax.service.ts`](frontend/src/app/services/fax.service.ts).

### 3. Log in

Login is a mock that runs only in the frontend. It works in dev builds only.

| Email | Password |
|---|---|
| `test1@gmail.com` | `12345678` |

---

## Configuration (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | The logging environment |
| `AI_PROVIDER` | `gemini` | `gemini` is the only implemented provider. Any other value falls back to rule-based extraction. |
| `AI_MODEL` | `gemini-flash-latest` | Use the `-latest` alias. Dated model names get retired and then return `NotFound`. |
| `AI_API_KEY` | *(empty)* | Your Gemini API key. If this is empty, the app uses rule-based extraction and turns chat off. |
| `MAX_FILE_SIZE_MB` | `10` | The largest upload allowed, in MB |
| `INVALID_MATCH_THRESHOLD` | `25` | A document whose match score (0–100) is below this is rejected as invalid. |
| `REVIEW_MATCH_THRESHOLD` | `60` | A match score below this sends the document to review. |
| `LOW_CONFIDENCE_THRESHOLD` | `0.70` | A field whose confidence is below this is flagged for review. |

---

## Demo walkthrough

1. Start both servers and open <http://localhost:4200>.
2. Click **Open Agent Simulation** and log in.
3. Go to **Fax Intake** and upload a PDF from [`sample-documents/`](sample-documents/):

   | File | What it shows |
   |---|---|
   | `valid_claim_full_match.pdf` | The complete, high-confidence path: every canonical field is present. |
   | `professional_insurance_claim.pdf` | A realistic formatted claim form, with labels and values on separate lines. |
   | `sample_fax_3_no_eligibility_match.pdf` | A prescription fax with no insurance fields. It shows the low-match / review path, where eligibility is not found. |

4. Watch the upload progress through each stage.
5. Review the extracted fields. Each field shows its confidence and whether it was verified against the source.
6. Ask the **AI Claim Manager** a question about the claim. You can type it or use the mic.
7. Edit any field you need to, then click **Approve & Resolve**. Open the audit log to see the recorded action.
8. From the **Dashboard**, go through the Transformation Factory funnel:
   - Growth Studio: discovery, architecture, implementation simulation, ROI and revenue.
   - Governance.
   - Managed Operations.

---

## API overview

All routes start with `/api`. Many claim routes also work under a `/faxes/...` path.

| Area | Endpoints |
|---|---|
| Health | `GET /health` |
| Documents | `POST /documents/upload`, `POST /documents/upload-async`, `GET /documents/upload-status/{job_id}`, `GET /documents/{id}` (plus `/status` and `/analysis`), `POST /documents/{id}/reprocess` |
| Claims | `GET /claims?status=all\|needs_review\|resolved\|invalid\|queued\|deleted`, `GET/PUT/DELETE /claims/{id}`, `POST /claims/{id}/restore`, `POST /faxes/{id}/decision`, `GET /claims/{id}/audit-log` |
| Chat | `GET/POST /claims/{id}/chat`, `POST /claims/{id}/chat/new`, `GET /claims/{id}/chat/quick-actions` |
| Dashboard | `GET /dashboard/statistics`, `/overview`, `/attention-summary`, `/providers`, `/export` (CSV) |
| TTS | `POST /ai/tts`, which returns `audio/wav` |
| Growth Studio | `POST /discovery/assess`, `GET /discovery/{id}`, `POST /implementation/simulate`, `POST /roi/calculate`, `POST /revenue/calculate` |
| Governance | `GET /governance/policy` |

For request and response schemas, see `/docs`.

---

## Running tests

```bash
cd backend
pytest
```

The test setup in `tests/conftest.py` blanks `AI_API_KEY`, so the suite always
uses the rule-based provider and never calls Gemini. The TTS tests need a
working text-to-speech engine on the machine. There are no frontend tests yet.

---

## Limitations and path to production

This is a hackathon MVP. Before production:

1. **Persistence:** everything is stored in memory in `backend/app/repositories/`
   and is lost when the server restarts. Replace these stores with a real
   database, such as Postgres.
2. **Eligibility:** `ELIGIBILITY_DB` in `backend/app/mock_db.py` is empty, so
   every lookup returns *Not Found*. Connect it to a real eligibility or
   insurer API.
3. **Authentication:** login is a frontend-only mock, and every API endpoint
   is open. Add backend authentication and RBAC.
4. **CORS:** `main.py` currently allows every origin (`*`). Restrict it to your
   frontend's origin.
5. **Configuration:** the frontend API URL is hardcoded in `fax.service.ts`.
   Move it into `environment*.ts`.
6. **Analytics roadmap:** a trained prediction model, an optimization solver
   and a feedback/learning loop are not built yet.

---

## Further documentation

- [`docs/hackfest-showcase/`](docs/hackfest-showcase/): executive summary, architecture, demo script, evidence mapping
- [`docs/diagrams/`](docs/diagrams/): lifecycle, technical architecture, chat grounding and governance routing diagrams
- [`build_prompt_ai_studio.md`](build_prompt_ai_studio.md): the original feature spec
