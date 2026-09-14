# Fax Intake — AI-Assisted Insurance Claim Processing

A working MVP implementing the fax-intake automation pipeline described in the
LLD: fax PDF → OCR/field extraction → eligibility lookup → confidence-based
auto-fill → human review → resolve. Built with **Angular** (frontend) and
**Python/FastAPI** (backend).

This is a **fully functional, tested application** — not just a mockup. The
backend pipeline has been verified end-to-end and the Angular app has been
successfully built.

## What's real vs. mocked

| Piece | Status |
|---|---|
| PDF text extraction | **Real** (PyMuPDF) — falls back to a mock fax if no text layer is found |
| Field extraction (name, DOB, member number, etc.) | **Rule-based regex** — swap for a real Claude/GPT-4V vision call or AWS Textract in production (see comments in `backend/app/agents/extraction.py`) |
| Confidence scoring | **Heuristic** — swap for real OCR/LLM confidence scores in production |
| Eligibility lookup | **Mock in-memory DB** — swap for the real eligibility API |
| Human approval / audit log | **Real** — fully functional, in-memory storage |

## Run the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for the interactive API docs (Swagger UI).

## Run the frontend

```bash
cd frontend
npm install
npm start
```

Visit `http://localhost:4200`. The app is pre-configured to call the backend
at `http://localhost:8000` (see `src/app/services/fax.service.ts`).

## Try it out

1. Start both servers above.
2. In the UI, click **"+ Upload Fax (PDF)"** and upload any PDF (or use the
   sample fax text embedded as a fallback — the pipeline will still run even
   if the PDF has no readable text).
3. Watch the AI Auto-Fill banner show overall confidence and any fields
   flagged for review (amber highlight vs. green).
4. Edit any field if needed, then click **"Approve & Resolve Fax"** — this
   calls the backend's human-in-the-loop decision endpoint and logs the
   action to the audit trail.

## Moving this to production

1. Replace `extract_fields_from_text()` in `backend/app/agents/extraction.py`
   with a real call to Claude's vision API or a document-AI service.
2. Replace `ELIGIBILITY_DB` in `backend/app/mock_db.py` with a real call to
   your eligibility API.
3. Replace the in-memory `FAXES` / `AUDIT_LOG` dicts in `backend/app/main.py`
   with a real database (Postgres recommended).
4. Add authentication (the current API has none — every endpoint is open).
5. Tighten the CORS policy in `main.py` to your real frontend origin.
6. See `build_prompt_ai_studio.md` for the full architecture/feature spec if
   you want an AI tool to extend this further.
