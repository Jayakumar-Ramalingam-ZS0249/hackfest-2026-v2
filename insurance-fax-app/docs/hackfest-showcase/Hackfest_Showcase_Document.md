# From Prediction to Governed Action
### Zuci Agent Services — Agentic Prescriptive Analytics Hackfest Showcase

> **Grounding statement:** Every claim below is traced to the `insurance-fax-app` repository (frontend: Angular 17.3; backend: FastAPI/Python; AI: Google Gemini). Labels — **[IMPLEMENTED]**, **[PARTIALLY IMPLEMENTED]**, **[PROPOSED]** — are applied strictly. Nothing is invented to fit the narrative.

---

## PAGE 1 — Executive Summary

**Message:** *"Prediction tells us what is likely to happen. Our solution focuses on what should happen next."*

Zuci Agent Services processes insurance claim documents end-to-end — upload, extraction, verification, policy-governed routing, and human-approved resolution. It is used here to demonstrate the layer most AI pitches skip: turning a computed signal (a confidence/relevance score) into a **governed, explainable, auditable action**, not just a number on a dashboard.

**What is proven today:**
- A real signal-to-decision pipeline: a document's relevance score and per-field AI confidence drive one of exactly three outcomes — auto-process, human-required, or reject — via three configured thresholds enforced in code.
- Four independent AI touch points, each following the same pattern: **the model drafts, deterministic code decides.**
- A real, live KPI layer (Governance, Managed Operations) computed from the same claim data the pipeline just produced — no batch delay.

**What is honestly not yet built:** a trained prediction model, an optimization engine that compares alternative actions, a feedback/learning loop, and multi-role access control. These are named plainly in Page 9 and throughout — they are the roadmap, not hidden gaps.

| Stage | Status |
|---|---|
| Data ingestion | [IMPLEMENTED] |
| Prediction (signal) | [PARTIALLY IMPLEMENTED] |
| Rules & Policy | [IMPLEMENTED] |
| Optimization | [PROPOSED] |
| AI Agent | [IMPLEMENTED] |
| Outcome | [IMPLEMENTED] |
| KPI | [IMPLEMENTED] |
| Learning | [PROPOSED] |
| Next Decision | [PARTIALLY IMPLEMENTED] |

---

## PAGE 2 — Current Business Problem

**Message:** Manual claim intake is slow, inconsistent, and stops at "here's a number" — a human still has to decide, unaided, what to do about it.

**Before (actual current workflow this application replaces):**

```text
DATA (faxed/scanned claim)
    |
ANALYST reads the document manually
    |
MANUAL REVIEW — retype up to 15 fields, cross-check by eye
    |
BUSINESS RULE CHECK — inconsistent, judgment-based, not codified
    |
DECISION — varies by reviewer, not recorded systematically
    |
ACTION
```

**Real pain points this application addresses:**
- A human must retype up to 15 fields per document (patient, policy, hospital, financial amounts).
- Faxed/scanned documents often have no text layer — ad hoc OCR or manual reading.
- Cross-checking a value against the source document is tedious and skipped under time pressure.
- No systematic way to catch a document with two conflicting values for the same field.
- "Is this even a valid claim?" is a subjective, reviewer-dependent judgment.
- No consistent, auditable policy for "auto-process vs. escalate vs. reject."

**SCREEN:** Fax Intake (`/queue/all`)
**PURPOSE:** Shows the exact document a reviewer would otherwise process by hand.
**DEMO ACTION:** Upload a real sample claim PDF.
**EXPECTED RESULT:** Real per-stage progress labels, not a spinner.
**BUSINESS MESSAGE:** "Every stage you see here replaces a manual step a reviewer used to do by hand."

---

## PAGE 3 — What Existing Solutions Do

| Capability | What it provides | Remaining limitation |
|---|---|---|
| Descriptive analytics [IMPLEMENTED] | Live counts, status distribution, confidence buckets (Governance/Managed Operations) | Describes what happened — does not decide what to do next |
| Diagnostic analytics [IMPLEMENTED] | Per-field confidence, source-page citation, conflict flags | Explains why a value looks uncertain — still needs a policy to act on it |
| Predictive analytics [PARTIALLY IMPLEMENTED] | Document relevance score + AI extraction confidence, computed per document | Not a trained forecasting model over historical outcomes |
| Rule-based decision systems [IMPLEMENTED] | Three configured thresholds route every claim identically | Rules alone can't draft a narrative recommendation or reason over unstructured text |
| Workflow automation [IMPLEMENTED] | Async upload → extraction → routing pipeline | Automates the pipeline, not the judgment call within it |
| Generative AI [IMPLEMENTED] | Gemini drafts field values, chat answers, process assessments, simulated agent output | A draft is not a decision until deterministic code checks it |
| Agentic AI [PARTIALLY IMPLEMENTED] | Four bounded, code-governed AI touch points | No autonomous multi-step planning — a fixed, human-defined sequence only |

This is not a criticism of any single capability — each does its job well. The gap is that **none of them, alone, closes the loop from signal to governed action to measured outcome.**

---

## PAGE 4 — What Gap Remains

**Prediction ≠ Decision.**

```text
Prediction / Signal
      |
Business Decision   <-- this step is where most systems leave a human unaided
      |
Action
      |
Outcome
```

What sits between a computed signal and a defensible action, in this application:

| Missing link | Present here? |
|---|---|
| Context (already-extracted claim fields) | [IMPLEMENTED] |
| Eligibility check | [PARTIALLY IMPLEMENTED] — deterministic lookup exists, backing data table is an empty placeholder |
| Rules / Policy | [IMPLEMENTED] — three configured thresholds |
| Constraints (whitelist, override rules) | [IMPLEMENTED] |
| Optimization (compare alternative actions) | [PROPOSED] |
| Explainability | [IMPLEMENTED] — source-text citation, named thresholds |
| Human approval | [IMPLEMENTED] — "Review Anyway", "Approve & Resolve" |
| Governance / audit | [IMPLEMENTED] — live Governance page, audit log |
| Outcome measurement (KPI) | [IMPLEMENTED] |
| Feedback / Learning | [PROPOSED] |

The honest gap: **Optimization and Learning.** Everything else needed to turn a signal into a governed, explainable action already exists and is demonstrable live.

---

## PAGE 5 — Our Solution: Agentic Prescriptive Analytics

**Message:** *"The innovation is not simply adding AI. The innovation is connecting signal, policy, and AI into a governed decision loop."*

```text
DATA -> PREDICTION -> RULES & POLICY -> OPTIMIZATION -> AI AGENT -> OUTCOME -> KPI -> LEARNING -> NEXT DECISION
```

Real implementation mapped to each stage:

| Stage | Real component | Status |
|---|---|---|
| Data | PDF upload, `agents/orchestrator.py` | [IMPLEMENTED] |
| Prediction | Relevance score + extraction confidence | [PARTIALLY IMPLEMENTED] |
| Rules & Policy | Three config thresholds, domain whitelist | [IMPLEMENTED] |
| Optimization | Fixed-formula ROI/Revenue calculators only | [PARTIALLY IMPLEMENTED] / true optimization [PROPOSED] |
| AI Agent | 4 bounded Gemini-backed agents | [IMPLEMENTED] |
| Outcome | Claim status transition, decision endpoint | [IMPLEMENTED] |
| KPI | Governance/Managed Operations analytics | [IMPLEMENTED] |
| Learning | — | [PROPOSED] |
| Next Decision | Same static thresholds re-applied to the next claim | [PARTIALLY IMPLEMENTED] |

**Key message:** *"AI provides contextual reasoning; deterministic controls provide governance."* This is demonstrated four separate times in the codebase, not once — extraction, chat, Discovery, Implementation each follow the same "model drafts, code decides" shape.

---

## PAGE 6 — End-to-End Architecture

```text
Angular 17 Frontend (standalone components, lazy routes)
    |
FastAPI Backend -- 10 route modules, consistent error contract
    |
Orchestration -- agents/orchestrator.py :: run_pipeline()
    |
Decision Layer
    +-- Prediction/Signal: DocumentRelevanceService, ClaimExtractionService
    +-- Rules: core/config.py thresholds (25 / 60 / 0.70)
    +-- Policy: Discovery agent whitelist, Implementation override rules
    +-- Optimization: ROI/Revenue calculators (fixed formula, not a solver) [PARTIAL]
    +-- AI Agent: Gemini via one shared AIProvider abstraction, RuleBasedProvider fallback
    |
Action Layer -- claim status transition, human Approve & Resolve
    |
Outcome / KPI -- Governance + Managed Operations (live, real-data views)
    |
Feedback / Learning -- [PROPOSED] -- not implemented today
```

**Actual technology stack (verified, not assumed):** Angular 17.3 (TypeScript, standalone components) · FastAPI (Python) · Google Gemini via `google-generativeai` · Tesseract OCR · PyMuPDF/pdfplumber for PDF parsing · in-memory Python dictionaries (no database) · no Node.js, no PostgreSQL, no Azure OpenAI, no OpenAI — these are **not** part of this stack and are not shown.

**SCREEN:** Governance (`/governance`)
**PURPOSE:** Proves the architecture's governance claim with live numbers, not a diagram.
**DEMO ACTION:** Open Governance immediately after resolving a claim.
**EXPECTED RESULT:** Decision-authority split changes in real time.
**BUSINESS MESSAGE:** "This isn't illustrative — these are the exact thresholds enforced on the document you just uploaded."

---

## PAGE 7 — Data → Prediction → Rules → Optimization → AI Agent → Outcome

**DATA [IMPLEMENTED]:** User-uploaded PDF claim documents (fax/scan) — the only data source; no external feed exists. Ingested via `POST /api/faxes/upload-async`, parsed by PyMuPDF/pdfplumber with a per-page Tesseract OCR fallback.

**PREDICTION [PARTIALLY IMPLEMENTED]:** Not a trained ML model. Two real, computed signals stand in for it: (1) `DocumentRelevanceService` — deterministic keyword-signal match score, 0–100; (2) per-field AI extraction confidence (Gemini JSON-mode, or rule-based fallback). Both are point-in-time, document-specific — not a forecast from historical outcomes.

**RULES & POLICY [IMPLEMENTED]:** Three configured thresholds (`core/config.py`): match score < 25 → reject; < 60 → human required; ≥ 60 with every field ≥ 70% confidence → auto-process. Separately, Discovery's domain-specific `AGENT_WHITELIST` and Implementation's override rules (skip AI below 60% confidence; force-flag missing diagnosis; force review if no patient name) are additional, code-enforced policy layers.

**OPTIMIZATION [PARTIALLY IMPLEMENTED / PROPOSED]:** Growth Studio's ROI and Revenue calculators are real, fixed-formula arithmetic (hours saved, per-stage fee estimate) — genuinely implemented, but this is estimation, not optimization. No solver compares alternative actions to select a best one anywhere in the codebase. **How this can be extended:** the same claim-context data already assembled for the AI Agent stage is the natural input to a future constrained-optimization step (e.g., prioritizing which needs-review claims a limited reviewer pool should work first, weighted by value/risk).

**AI AGENT [IMPLEMENTED]:** Four bounded agents — Claim Extraction, AI Claim Manager (grounded chat), Discovery, Implementation — each a single Gemini call followed immediately by a deterministic check. No autonomous multi-step loop; not claimed as such.

**OUTCOME [IMPLEMENTED]:** Claim status set to `auto_filled` / `needs_review` / `resolved` / `invalid`; the only way to `resolved` is an explicit human "Approve & Resolve."

**SCREEN:** Fax Intake claim detail
**PURPOSE:** Shows the entire signal → policy → agent → outcome chain on one screen.
**DEMO ACTION:** Click "View Source" on a field, then "Approve & Resolve."
**EXPECTED RESULT:** Source snippet highlighted; claim status becomes Resolved.
**BUSINESS MESSAGE:** "Every value is traceable, and the human — not the model — makes the final call."

---

## PAGE 8 — KPI → Learning → Next Decision

**KPI [IMPLEMENTED]** — real fields computed by `analytics_service.py`, not illustrative numbers:

| KPI | Source field | Business meaning |
|---|---|---|
| Total / Pending / Resolved / Invalid claims | `summary.*` | Volume and backlog at a glance |
| Total / Approved / Pending / Rejected claim value | `financial.*` (INR) | Financial exposure by state |
| Status distribution (%) | `statusDistribution` | Real, not hardcoded, percentage split |
| High / Medium / Low confidence fields | `quality.*ConfidenceFields` | Extraction reliability |
| Source-mapping success rate | `quality.sourceMappingSuccessRate` | % of fields with a verifiable citation |
| OCR required vs. completed | `documentAnalytics.ocrRequired/ocrCompleted` | Scan-quality operational load |
| Attention-required queue (HIGH/MEDIUM/LOW) | `attentionRequired` | Prioritized real work backlog |

**LEARNING [PROPOSED]:** A manager's field correction updates only the current claim record. It is **not** fed back into the extraction model, the three thresholds, or the agent whitelist. No expected-vs-actual outcome tracking exists. This is the clearest, most valuable next build item.

**NEXT DECISION [PARTIALLY IMPLEMENTED]:** The loop restarts at Data for the next uploaded claim, using the **same static thresholds** every time — there is closure of the pipeline, but not yet adaptive closure of the loop (thresholds don't tune themselves from outcomes).

**SCREEN:** Governance (`/governance`) → "Recent Decision Audit Trail"
**PURPOSE:** Proves KPIs are live, not mocked.
**DEMO ACTION:** Refresh after approving a claim.
**EXPECTED RESULT:** Decision-authority split and audit trail update immediately.
**BUSINESS MESSAGE:** "No reporting lag — Governance reads the same store the pipeline just wrote."

---

## PAGE 9 — Business Value + Innovation

- **Faster, consistent decisions** — one policy, applied identically, every time, not a judgment call that varies by reviewer.
- **From signal to action** — a confidence score doesn't just sit on a dashboard; it drives a real routing decision, in code.
- **Explainable by construction** — every value cites its source page; every routing decision names its threshold.
- **Repeatable governance pattern** — "model drafts, code decides" proven four times, not once, which is evidence it generalizes.
- **Augments, doesn't replace** — the architecture is designed to sit on top of existing predictive signals rather than requiring a rebuilt model.

**Implemented vs. Proposed — capability matrix**

| Capability | Status |
|---|---|
| PDF upload + async pipeline | [IMPLEMENTED] |
| OCR fallback | [IMPLEMENTED] |
| AI field extraction + rule-based fallback | [IMPLEMENTED] |
| Source verification / conflict detection | [IMPLEMENTED] |
| Policy-threshold routing | [IMPLEMENTED] |
| Human approval gate | [IMPLEMENTED] |
| Grounded AI chat | [IMPLEMENTED] |
| Agent whitelist enforcement | [IMPLEMENTED] |
| Confidence-based override rules | [IMPLEMENTED] |
| Live KPI / audit trail | [IMPLEMENTED] |
| Eligibility lookup | [PARTIALLY IMPLEMENTED] — deterministic, but backing table is empty |
| ROI / Revenue estimation | [IMPLEMENTED] (arithmetic, not optimization) |
| True optimization (alternative-action comparison) | [PROPOSED] |
| Feedback / learning loop | [PROPOSED] |
| Multi-role RBAC | [PROPOSED] |
| Backend authentication | [PROPOSED] |
| Trained prediction model | [PROPOSED] |

---

## PAGE 10 — Hackfest Demo Journey + Final Takeaway

**Journey:** Problem → Why prediction alone is insufficient → The missing decision layer → How our solution closes the loop → Live demo → Business value → Closed-loop roadmap.

**Live demo sequence (see `Hackfest_Demo_Script.md` for full timing):**
1. Upload a real claim → watch the real per-stage pipeline.
2. Point at the confidence/match score — "this is our signal, not a trained prediction — we say that plainly."
3. Open Governance — the exact thresholds that just routed this claim.
4. Approve & Resolve — the only path to a final decision is a human action.
5. Refresh Governance — KPIs update live, no batch delay.

**Final takeaway:**
> "We are not pitching a new prediction model. We are showing the governed decision layer that sits on top of one — proven four separate times in a single working application — and we are naming, plainly, the two pieces (optimization and learning) needed to close the loop completely."

