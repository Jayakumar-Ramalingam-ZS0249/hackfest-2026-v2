# Hackfest Demo Script (10 minutes)
### Zuci Agent Services — "From Prediction to Governed Action"

Narrative spine: **Problem → Why existing approach is not enough → Gap → Our innovation → How it works → Live demo → Business value → Closed-loop learning.**

Do not narrate this as "here are our screens." Narrate it as: *"Here is the business problem. Here is why a signal alone is insufficient. Here is the missing decision layer. Here is how our solution closes the loop."*

---

## 0:00 – 1:00 — Business Problem

**WHAT TO SHOW:** Nothing yet — talk to the room.
**WHAT TO SAY:** "Every claims team still manually reads faxed documents, retypes fields, and decides case-by-case whether something needs escalation. That's slow, and it's inconsistent between reviewers."
**WHAT TO CLICK:** —
**EXPECTED RESULT:** —
**KEY MESSAGE:** *"Prediction tells us what is likely to happen. We're here to show what should happen next."*

---

## 1:00 – 2:00 — Existing Solution

**WHAT TO SHOW:** Governance page (`/governance`), scrolled to the top.
**WHAT TO SAY:** "Descriptive analytics, confidence scoring, generative AI drafting — these all already exist and work well in this build. What none of them alone does is close the loop from a signal to a governed, measured action."
**WHAT TO CLICK:** Nothing yet — just orient the audience on the page.
**EXPECTED RESULT:** Live threshold cards visible.
**KEY MESSAGE:** *"We're not replacing existing predictive investment — we're augmenting it."*

---

## 2:00 – 3:00 — Prediction-to-Action Gap

**WHAT TO SHOW:** The architecture diagram (`Hackfest_Architecture.md` / `Hackfest_Workflow.mmd`).
**WHAT TO SAY:** "A confidence score is not a decision. Someone still has to decide whether 72% confident is good enough to act on — consistently, auditably. That's the gap."
**WHAT TO CLICK:** Point at the diagram, top to bottom.
**EXPECTED RESULT:** —
**KEY MESSAGE:** *"Prediction ≠ Decision."*

---

## 3:00 – 4:00 — Our Solution

**WHAT TO SHOW:** Dashboard (`/dashboard`) — the Transformation Factory funnel.
**WHAT TO SAY:** "Every stage of the decision journey — Discovery, Blueprinting, Implementation, Governance, Managed Operations — is a real click here, not five separate slides."
**WHAT TO CLICK:** Point at each funnel card.
**EXPECTED RESULT:** —
**KEY MESSAGE:** *"The innovation is connecting signal, policy, and AI into a governed loop — not just adding AI."*

---

## 4:00 – 6:00 — Live Application Demo

**WHAT TO SHOW:** Fax Intake (`/queue/all`).
**WHAT TO SAY:** "Watch the real per-stage progress — uploading, OCR, relevance check, AI extraction, verification, eligibility. These are actual pipeline stages reporting back, not a timer."
**WHAT TO CLICK:** Upload a real sample PDF (`sample-documents/professional_insurance_claim.pdf`); wait for the field-by-field auto-fill reveal.
**EXPECTED RESULT:** Fields populate one at a time with confidence badges and source-page links.
**KEY MESSAGE:** *"Every value is source-verified — click 'View Source' and I'll show you exactly where it came from."*

---

## 6:00 – 7:30 — Rules + Optimization + AI Agent

**WHAT TO SHOW:** The claim detail's AI Claim Manager panel, then Growth Studio → Implementation tab.
**WHAT TO SAY:** "Ask a quick-action question — that's answered with zero AI calls, pure lookup. Ask an open-ended one — that goes to Gemini, but the answer is discarded unless its cited source text is verified in the context we actually sent. Now watch Implementation: if confidence is under 60%, the code skips the AI call entirely and forces escalation. That's not a prompt instruction — it's a hard rule in Python."
**WHAT TO CLICK:** Ask one quick-action question, one open-ended question; then run a simulation on a low-confidence claim.
**EXPECTED RESULT:** Instant answer for the quick action; a real Gemini call for the open-ended one; forced "Escalate to Human Review" on the low-confidence simulation.
**KEY MESSAGE:** *"AI provides contextual reasoning; deterministic controls provide governance."* Optimization note: "Our ROI/Revenue tabs are real arithmetic — I'll say plainly that comparing alternative actions to pick an optimum is not built yet; that's on our roadmap, not hidden."

---

## 7:30 – 8:30 — Recommendation + Governance

**WHAT TO SHOW:** Governance page, right after the upload from step 4-6.
**WHAT TO SAY:** "These aren't illustrative numbers. This is the exact threshold — 25% reject, 60% review, 70% per-field confidence — that just decided the claim you watched upload."
**WHAT TO CLICK:** Open Governance; point at "Decision Policy — Live Thresholds" and "Decision Authority — Who Decided."
**EXPECTED RESULT:** The split reflects the claim just processed.
**KEY MESSAGE:** *"Governance is not a slide — it's a live read of the same enforcement code."*

---

## 8:30 – 9:15 — Outcome + KPI

**WHAT TO SHOW:** Back to the claim detail; click "Approve & Resolve"; return to Governance.
**WHAT TO SAY:** "That decision is now permanent, logged, and immediately reflected — no batch delay, because there's no batch layer. The KPIs you see are computed live from the same claim store."
**WHAT TO CLICK:** Approve & Resolve → refresh Governance.
**EXPECTED RESULT:** Decision-authority split and audit trail update.
**KEY MESSAGE:** *"The decision doesn't end with the recommendation — the outcome becomes visible, live, immediately."*

---

## 9:15 – 10:00 — Learning + Next Decision

**WHAT TO SHOW:** Nothing new on screen — closing remarks over the Governance page.
**WHAT TO SAY:** "I'll be direct about what's next: today, a manager's correction updates only that one claim — it doesn't yet tune our thresholds or retrain anything. Closing that feedback loop, and adding a genuine optimization step for prioritizing the review queue, are our two clearest next builds. Everything else in the Data-to-KPI chain is real, working, and what you just watched."
**WHAT TO CLICK:** —
**EXPECTED RESULT:** —
**KEY MESSAGE:** *"We move from isolated predictions to continuous decision intelligence — and we're honest about exactly how much of that loop is closed today."*

---

## Presenter Checklist

- [ ] Backend running, `/api/health` confirmed
- [ ] Frontend logged in with the demo credential
- [ ] A clean sample PDF ready, plus a low-confidence/irrelevant one for the reject/escalate path
- [ ] `AI_API_KEY` configured (and know how to unset it live to show the deterministic fallback)
- [ ] At least one claim already processed this session so Governance isn't showing all-zero
- [ ] The three threshold numbers memorized: 25% / 60% / 70%
- [ ] Rehearsed the honest-gaps list (optimization, learning, RBAC, backend auth) so no judge question gets an evasive answer
