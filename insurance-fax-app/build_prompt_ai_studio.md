# Master Build Prompt — AI-Assisted Fax Intake Tool for Insurance Claims

> Paste this into an AI app-builder tool (Google AI Studio, Claude Code, Cursor, etc.) to generate or extend this application. A working reference implementation is already included alongside this prompt — use it as the starting point rather than building from zero.

---

## 1. What You're Building

A **production-track internal tool** for a Clinical Admin / Claims Manager who processes incoming insurance-claim faxes. Today, staff read patient and prescription details off a fax preview and manually type them into an intake form. This tool automates that: it extracts the fields with AI, auto-fills the form for anything it's confident about, and flags anything it isn't — with the human always making the final call before a fax is marked Resolved.

**Audience:** internal clinical/claims staff (not an external sales demo) — so prioritize speed, clarity, and trustworthiness over marketing polish. It should feel like software a hospital or insurer's back office actually runs every day.

---

## 2. Tech Stack

- **Frontend:** Angular 17+ (standalone components, no NgModule boilerplate), TypeScript, SCSS
- **Backend:** Python, FastAPI
- **PDF/OCR:** PyMuPDF (`fitz`) for text-based PDFs; add Tesseract OCR as a fallback for scanned/image-only faxes
- **AI extraction (production):** a vision-capable LLM (Claude) or a document-AI service (AWS Textract / Azure Document Intelligence) for messy or handwritten faxes — the reference implementation uses a rule-based regex extractor as a zero-dependency stand-in; swap it out at `backend/app/agents/extraction.py`
- **Data:** in-memory for this MVP; swap for Postgres in production

---

## 3. Visual Theme (must match attached reference screenshot: "Medical Command Center")

- **Layout:** left sidebar (brand + navigation with status badges: Fax Intake, Resolved, Sent, Queued, Needs Review, Failed, Deleted, Locked), top header bar with app name and logged-in user, main content area
- **AI status banner:** a full-width colored banner at the top of the main content area stating overall confidence (e.g. "AI Auto-Fill Active — 94% Overall Confidence") with action buttons ("Re-run Extraction", "Approve & Resolve Fax")
- **Two-panel layout below the banner:**
  - Left: **Patient Information** form — each field shows an inline confidence badge (green checkmark + percentage for high confidence, amber warning + percentage for "Review" status), plus a read-only **Eligibility** sub-section (Client, Plan, Group No., Eligibility Status) pulled from a database lookup
  - Right: **Received Document** panel — the fax preview (text or image), ideally with highlighted regions showing what was matched to which field ("OCR Bounding Box: Patient Name" style tags)
- **Color language:** deep blue for branding/primary actions, green for high-confidence/success states, amber for needs-review states, red for errors/deletion — consistent throughout
- **Typography:** clean sans-serif (Inter), rounded cards (12–20px radius), soft shadows, generous spacing — professional clinical-software aesthetic, not sterile/dense like the legacy tool being replaced

---

## 4. Pipeline Architecture (must follow this exact division of labor)

This follows the same governance principle as any agentic system handling regulated data: **the AI orchestrates and explains, but every consequential number/decision is produced by a deterministic, auditable function** — never by the LLM "reasoning" its way to an answer.

```
Fax received
  → Preprocess agent      (image cleanup — deskew/rotate/enhance)
  → Extraction agent      (OCR + LLM → structured JSON with per-field confidence)
  → Mapping agent         (normalize labels onto the canonical field schema)
  → Eligibility match agent (query patient DB by Member Number/Name/DOB)
  → Confidence/QA agent   (per-field: auto-fill vs. flag for review — simple
                            threshold logic, NO LLM, since this touches the
                            live patient database and must stay deterministic)
  → Auto-fill agent       (writes confirmed values into the UI form)
  → Human review          (user confirms/corrects flagged fields)
  → Save / resolve fax    (corrections logged for future retraining)
```

### Tool Registry (Python functions — the closed set of things any LLM step may call)
```
extract_text_from_pdf(pdf_bytes) -> raw_text
extract_fields_from_text(raw_text) -> {field: {value, confidence}}
run_eligibility_lookup(fields) -> {client, plan, group_no, eligibility_status, found}
decide_field_status(field_name, confidence) -> "auto_fill" | "needs_review"
```

### Confidence Thresholds (tunable per field — this is a compliance control, not a UI preference)
- Member Number: **95%+** required (drives the eligibility lookup — a wrong number pulls up the wrong patient)
- Name / DOB: 90%+
- City / State: 70%+ (lower stakes)
- Drug / Physician: 80–85%

---

## 5. Data Schema

```json
{
  "id": "c51d3b4a",
  "filename": "prior_auth_fax.pdf",
  "received_at": "2026-09-07T03:36:06Z",
  "fields": {
    "first_name": { "value": "Jonathan", "confidence": 0.99, "status": "auto_fill" },
    "last_name": { "value": "Reynolds", "confidence": 0.99, "status": "auto_fill" },
    "member_number": { "value": "MRN-8849-X", "confidence": 0.82, "status": "needs_review" },
    "dob": { "value": "11/14/1978", "confidence": 0.98, "status": "auto_fill" }
  },
  "eligibility": {
    "found": true,
    "client": "Metro Health Alliance",
    "plan": "PPO Gold",
    "group_no": "GRP-4471",
    "eligibility_status": "Active"
  },
  "overall_confidence": 93.0,
  "needs_review_count": 1,
  "status": "needs_review",
  "provenance": [ { "tool": "extraction_agent", "run_id": "...", "timestamp": "..." } ]
}
```

---

## 6. API Endpoints (FastAPI)

```
POST /api/faxes/upload              → run the full pipeline on an uploaded PDF
GET  /api/faxes                     → list all faxes (queue view)
GET  /api/faxes/{id}                → full detail for one fax
POST /api/faxes/{id}/decision       → human approves/corrects, moves to Resolved
GET  /api/faxes/{id}/audit-log      → full audit trail for one fax
```

---

## 7. Compliance Requirements (non-negotiable — this is PHI)

- Any OCR/LLM vendor used in production **must have a signed BAA and be HIPAA-eligible**
- Full audit trail: every field must record what was auto-filled vs. corrected, and by whom
- No fax may reach "Resolved" status without an explicit human decision — no full automation without a human checkpoint, even at high confidence, until the rollout has proven itself (see rollout phases below)

---

## 8. Suggested Rollout Phases

1. **Pilot (shadow mode)** — run extraction in parallel with the current manual process; measure accuracy without changing the workflow
2. **Assisted fill** — auto-populate fields but require user confirmation before saving (this is what the reference implementation demonstrates)
3. **Full automation** — auto-save high-confidence faxes straight to Resolved; route low-confidence ones to the review queue

---

## 9. What's Already Built (reference implementation included)

A working version of this exact spec is included in this package:
- `backend/` — FastAPI app implementing the full pipeline with mock extraction/eligibility logic, tested end-to-end
- `frontend/` — Angular app matching the theme described above, verified to build with zero errors

Use these as the scaffold. The main production work remaining is:
1. Swapping the mock extraction logic for a real vision-LLM or document-AI call
2. Swapping the mock eligibility DB for the real eligibility API
3. Adding authentication and a persistent database
4. Adding the image-preview-with-bounding-boxes feature (currently shows raw text only)
