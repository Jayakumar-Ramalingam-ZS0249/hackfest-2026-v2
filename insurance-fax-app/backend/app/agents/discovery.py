"""
Discovery agent.

Assesses a business process description and recommends which agents
could automate it. Follows the same division-of-labor rule as the rest
of this app (see extraction/claim_extraction_service.py and
eligibility.py): the LLM only drafts suggestions -- the actual
guardrail is the whitelist filter below, enforced in code, which runs
regardless of whether the LLM behaved. An instruction in a prompt is
not a guardrail.
"""

import logging
import re

from ..core.exceptions import InvalidDocumentError
from ..services.ai.base import AIProvider

logger = logging.getLogger("app.agents.discovery")

MAX_PROCESS_TEXT_CHARS = 20_000

AGENT_WHITELIST: dict[str, list[str]] = {
    "healthcare": ["Document Intake Agent", "Clinical Agent", "Policy Agent", "Workflow Agent"],
    "collections": ["Risk Agent", "Settlement Agent", "Communication Agent"],
    "customer_service": ["Knowledge Agent", "Routing Agent", "Support Agent"],
    "general": ["Document Intake Agent", "Workflow Agent"],
}

# Used only by the deterministic fallback assessment below -- keyword
# signals that make the score/actor count actually respond to what was
# typed, instead of one flat number regardless of input.
ROLE_KEYWORDS = [
    "reviewer", "agent", "clerk", "manager", "clinician", "representative",
    "specialist", "officer", "staff", "nurse", "doctor", "adjuster", "analyst",
    "coordinator", "supervisor", "technician",
]
AUTOMATABLE_ACTION_KEYWORDS = [
    "check", "verify", "review", "record", "send", "notify", "calculate",
    "validate", "approve", "route", "extract", "confirm", "update", "match",
    "lookup", "flag", "escalate", "classify",
]

# Keyword lists used for deterministic domain classification -- this runs
# in code, never via an LLM call, because it gates which agents are even
# allowed to be recommended in the prompt below.
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "healthcare": [
        "diagnosis", "patient", "fax", "clinical", "prior auth", "prior authorization",
        "physician", "hospital", "claim", "medical", "member id", "policy number",
    ],
    "collections": [
        "collections", "delinquent", "payment plan", "debt", "settlement",
        "past due", "arrears", "creditor", "charge-off", "charge off",
    ],
    "customer_service": [
        "ticket", "support", "customer", "help desk", "helpdesk", "inquiry", "complaint", "call center",
    ],
}

DISCOVERY_PROMPT = """You are a process automation consultant. Read the business process
description below and draft an automation assessment.

Only recommend agents from this exact list: {whitelist}. Do not invent agent
names outside this list.

Return ONLY valid JSON with this exact shape, no extra commentary:
{{
  "process_name": "<short name for this process>",
  "human_actors": <integer, estimated number of distinct human roles involved>,
  "manual_touchpoints": <integer, estimated number of manual hand-off steps>,
  "agent_suitability_score": <integer 0-100>,
  "recommended_agents": ["<agent name>", ...],
  "current_state": "<1-3 sentence description of today's manual process>",
  "future_state": "<1-3 sentence description of the automated process>",
  "roadmap": ["<step 1>", "<step 2>", "..."]
}}

Process description:
---
{process_text}
---
"""


def classify_domain(process_text: str) -> str:
    """Deterministic keyword classification -- code-level, not an LLM call."""
    text = (process_text or "").lower()
    scores = {domain: sum(1 for kw in keywords if kw in text) for domain, keywords in DOMAIN_KEYWORDS.items()}
    best_domain = max(scores, key=scores.get)
    return best_domain if scores[best_domain] > 0 else "general"


def _validate_process_text(process_text: str) -> None:
    if not process_text or not process_text.strip():
        raise InvalidDocumentError("The process description is empty. Please provide at least one step.")
    if len(process_text) > MAX_PROCESS_TEXT_CHARS:
        raise InvalidDocumentError(
            f"Process description too large ({len(process_text):,} characters). "
            f"Maximum supported size is {MAX_PROCESS_TEXT_CHARS:,} characters."
        )


def _split_into_steps(process_text: str) -> list[str]:
    """Breaks the process description into distinct steps.

    Prefers real line breaks (one step per line). If the whole thing is a
    single line -- very common when a description is pasted from an email
    or chat -- falls back to numbered-list markers ("1.", "2)"), then to
    plain sentence boundaries, so a pasted paragraph still counts as
    several steps instead of always looking like just one.
    """
    lines = [line.strip() for line in re.split(r"[\n\r]+", process_text) if line.strip()]
    if len(lines) > 1:
        return lines

    numbered = [s.strip() for s in re.split(r"(?<!\d)\d+[.)]\s+", process_text) if s.strip()]
    if len(numbered) > 1:
        return numbered

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", process_text) if s.strip()]
    return sentences or [process_text.strip()]


def _fallback_assessment(process_text: str, domain: str, whitelist: list[str]) -> dict:
    """Deterministic assessment used when no AI provider is configured (or
    the AI call failed/rate-limited) -- this app must keep working
    end-to-end with zero external AI, same principle as the rule-based
    extraction fallback. Every number below is derived from the actual
    input text, not a fixed constant, so two different processes produce
    two different assessments even without AI available.
    """
    steps = _split_into_steps(process_text)
    step_count = max(len(steps), 1)
    text_lower = process_text.lower()

    role_hits = {kw for kw in ROLE_KEYWORDS if kw in text_lower}
    human_actors = max(len(role_hits), (step_count + 1) // 2)
    human_actors = max(1, min(human_actors, 8))

    action_hits = sum(1 for kw in AUTOMATABLE_ACTION_KEYWORDS if kw in text_lower)
    score = 42 + min(action_hits * 6, 36) + min(step_count * 2, 16)
    score = max(30, min(score, 92))

    return {
        "process_name": f"{domain.replace('_', ' ').title()} Process",
        "human_actors": human_actors,
        "manual_touchpoints": step_count,
        "agent_suitability_score": score,
        "recommended_agents": list(whitelist),
        "current_state": (
            f"This process runs manually across {step_count} step{'s' if step_count != 1 else ''} and "
            f"{human_actors} distinct role{'s' if human_actors != 1 else ''}, with a hand-off at each stage."
        ),
        "future_state": f"An agent team ({', '.join(whitelist)}) automates the repetitive steps of this process.",
        "roadmap": ["Assess current process", "Pilot agent architecture", "Roll out to production", "Monitor and tune"],
    }


def run_discovery(process_text: str, ai_provider: AIProvider) -> dict:
    """Classifies the process, drafts (or falls back to) an assessment, and
    enforces the agent whitelist in code before returning anything."""
    _validate_process_text(process_text)

    domain = classify_domain(process_text)
    whitelist = AGENT_WHITELIST[domain]

    if ai_provider.name == "rule_based":
        result = _fallback_assessment(process_text, domain, whitelist)
        assessment_source = "rule_based"
    else:
        prompt = DISCOVERY_PROMPT.format(whitelist=whitelist, process_text=process_text[:MAX_PROCESS_TEXT_CHARS])
        try:
            result = ai_provider.generate_json(prompt)
            assessment_source = ai_provider.name
        except Exception as exc:
            logger.warning("discovery_ai_call_failed: %s", exc)
            result = _fallback_assessment(process_text, domain, whitelist)
            assessment_source = "rule_based"

    # --- Hallucination guardrail: enforced in code, never just prompted for. ---
    raw_agents = result.get("recommended_agents") or []
    filtered_agents = [a for a in raw_agents if a in whitelist]
    rejected_agents = [a for a in raw_agents if a not in whitelist]
    if rejected_agents:
        logger.warning("discovery_filtered_out_of_whitelist_agents: %s (domain=%s)", rejected_agents, domain)
    if not filtered_agents:
        # Never hand back an architecture with zero agents -- fall back to
        # the full whitelist rather than showing an empty recommendation.
        filtered_agents = list(whitelist)
    assert all(agent in whitelist for agent in filtered_agents), "whitelist filter failed to enforce membership"

    return {
        "process_name": result.get("process_name") or f"{domain.replace('_', ' ').title()} Process",
        "domain": domain,
        "whitelist": whitelist,
        "human_actors": max(0, int(result.get("human_actors") or 1)),
        "manual_touchpoints": max(0, int(result.get("manual_touchpoints") or 1)),
        "agent_suitability_score": max(0, min(100, int(result.get("agent_suitability_score") or 0))),
        "recommended_agents": filtered_agents,
        "rejected_agents": rejected_agents,
        "current_state": result.get("current_state") or "Not available.",
        "future_state": result.get("future_state") or "Not available.",
        "roadmap": result.get("roadmap") or [],
        "assessment_source": assessment_source,
    }
