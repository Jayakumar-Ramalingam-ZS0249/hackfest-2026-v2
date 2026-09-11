"""Plain Python tool functions — the ONLY place any real computation happens in
the claims-review pipeline. The AI orchestration layer (app.agent) decides
*when* to call these and *in what order*, but it never verifies an identity,
detects fraud, checks compliance, or calculates an approved amount itself:
those results only ever come from this module.

Every tool is wrapped with @traced (app.agent.provenance) so each invocation is
recorded in the audit log automatically, and every tool takes only an
`applicant_id` — the trusted server-side record is looked up here, so nothing
the AI (or a client) supplies can be substituted into the computation itself.
"""

import re
from typing import Any, Dict

from app import store
from app.agent.provenance import traced

_AADHAR_RE = re.compile(r"^[0-9Xx]{4}-[0-9Xx]{4}-\d{4}$")
_PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")

# --- Business rule constants (kept together and named so the rationale writer
# and the UI can reference exactly why a threshold was crossed) ------------
MAX_RISK_PENALTY_FRACTION = 0.50
TENURE_BONUS_PER_YEAR = 0.02
MAX_TENURE_BONUS_YEARS = 5
PRIOR_CLAIMS_PENALTY_PER_CLAIM = 0.03
MAX_PRIOR_CLAIMS_CONSIDERED = 5

FRAUD_RISK_THRESHOLD = 0.80
FRAUD_PRIOR_CLAIMS_THRESHOLD = 3
FRAUD_HIGH_AMOUNT_THRESHOLD = 200_000
FRAUD_EARLY_CLAIM_AMOUNT_THRESHOLD = 450_000
FRAUD_EARLY_CLAIM_TENURE_THRESHOLD = 1

MIN_POLICY_TENURE_YEARS = 1
MATERNITY_MIN_TENURE_YEARS = 2
MAX_CLAIM_AMOUNT = 500_000


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@traced("verify_identity")
def verify_identity(applicant_id: str) -> Dict[str, Any]:
    """Confirms Aadhar/PAN identity documents against the system of record.
    In production this would call an external KYC/UIDAI + PAN verification
    service; this demo checks document format and the verification flag
    already on file, which stands in for that external call."""
    applicant = store.require_applicant(applicant_id)
    aadhar_format_ok = bool(_AADHAR_RE.match(applicant.aadhar_number or ""))
    pan_format_ok = bool(_PAN_RE.match(applicant.pan_number or ""))
    return {
        "aadhar_valid": bool(applicant.aadhar_verified and aadhar_format_ok),
        "pan_valid": bool(applicant.pan_verified and pan_format_ok),
        "aadhar_format_ok": aadhar_format_ok,
        "pan_format_ok": pan_format_ok,
    }


@traced("check_fraud_flags")
def check_fraud_flags(applicant_id: str) -> Dict[str, Any]:
    a = store.require_applicant(applicant_id)
    reasons = []

    if (
        a.prior_claims_count >= FRAUD_PRIOR_CLAIMS_THRESHOLD
        and a.claim_amount_requested > FRAUD_HIGH_AMOUNT_THRESHOLD
    ):
        reasons.append(
            f"{a.prior_claims_count} prior claims combined with a high claim amount "
            f"(₹{a.claim_amount_requested:,.0f}) exceeds the multi-claim pattern threshold"
        )
    if a.risk_score >= FRAUD_RISK_THRESHOLD:
        reasons.append(
            f"Risk score {a.risk_score:.2f} meets or exceeds the high-risk threshold "
            f"({FRAUD_RISK_THRESHOLD:.2f})"
        )
    if (
        a.claim_amount_requested >= FRAUD_EARLY_CLAIM_AMOUNT_THRESHOLD
        and a.policy_tenure_years <= FRAUD_EARLY_CLAIM_TENURE_THRESHOLD
    ):
        reasons.append(
            f"Large claim (₹{a.claim_amount_requested:,.0f}) filed within the first "
            f"{FRAUD_EARLY_CLAIM_TENURE_THRESHOLD} year(s) of the policy"
        )
    if not a.aadhar_verified or not a.pan_verified:
        reasons.append("Unverified identity document(s) on file")

    return {"flagged": len(reasons) > 0, "reasons": reasons}


@traced("check_policy_compliance")
def check_policy_compliance(applicant_id: str) -> Dict[str, Any]:
    a = store.require_applicant(applicant_id)

    if a.policy_tenure_years < MIN_POLICY_TENURE_YEARS:
        return {
            "compliant": False,
            "reason": (
                f"Policy tenure of {a.policy_tenure_years} year(s) is below the "
                f"{MIN_POLICY_TENURE_YEARS}-year minimum waiting period"
            ),
        }
    if a.claim_type == "Maternity" and a.policy_tenure_years < MATERNITY_MIN_TENURE_YEARS:
        return {
            "compliant": False,
            "reason": f"Maternity claims require at least {MATERNITY_MIN_TENURE_YEARS} years of policy tenure",
        }
    if a.claim_amount_requested > MAX_CLAIM_AMOUNT:
        return {
            "compliant": False,
            "reason": f"Claim amount exceeds the policy sub-limit of ₹{MAX_CLAIM_AMOUNT:,.0f}",
        }
    return {"compliant": True, "reason": "Claim satisfies standard policy terms"}


@traced("calculate_risk_adjusted_amount")
def calculate_risk_adjusted_amount(applicant_id: str) -> Dict[str, Any]:
    a = store.require_applicant(applicant_id)
    risk_score = _clamp(a.risk_score, 0.0, 1.0)

    tenure_bonus = min(a.policy_tenure_years, MAX_TENURE_BONUS_YEARS) * TENURE_BONUS_PER_YEAR
    risk_penalty = risk_score * MAX_RISK_PENALTY_FRACTION
    prior_claims_penalty = (
        min(a.prior_claims_count, MAX_PRIOR_CLAIMS_CONSIDERED) * PRIOR_CLAIMS_PENALTY_PER_CLAIM
    )
    approval_fraction = _clamp(1.0 - risk_penalty - prior_claims_penalty + tenure_bonus, 0.0, 1.0)
    approved_amount = round(a.claim_amount_requested * approval_fraction / 100.0) * 100.0

    return {
        "approved_amount": approved_amount,
        "approval_fraction": round(approval_fraction, 4),
        "risk_penalty": round(risk_penalty, 4),
        "prior_claims_penalty": round(prior_claims_penalty, 4),
        "tenure_bonus": round(tenure_bonus, 4),
    }


TOOL_FUNCTIONS = {
    "verify_identity": verify_identity,
    "check_fraud_flags": check_fraud_flags,
    "check_policy_compliance": check_policy_compliance,
    "calculate_risk_adjusted_amount": calculate_risk_adjusted_amount,
}

# JSON tool schemas handed to Claude. Every schema takes only `applicant_id` —
# see the module docstring for why.
CLAUDE_TOOL_SCHEMAS = [
    {
        "name": "verify_identity",
        "description": (
            "Verify the applicant's Aadhar and PAN identity documents against the system of "
            "record. Always call this first for any new review."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "applicant_id": {"type": "string", "description": "The applicant ID, e.g. APP-1001"},
            },
            "required": ["applicant_id"],
        },
    },
    {
        "name": "check_fraud_flags",
        "description": "Run rule-based fraud detection checks on the applicant's claim history and profile.",
        "input_schema": {
            "type": "object",
            "properties": {
                "applicant_id": {"type": "string", "description": "The applicant ID, e.g. APP-1001"},
            },
            "required": ["applicant_id"],
        },
    },
    {
        "name": "check_policy_compliance",
        "description": (
            "Check whether the claim complies with policy terms: waiting periods, claim-type "
            "rules, and sub-limits."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "applicant_id": {"type": "string", "description": "The applicant ID, e.g. APP-1001"},
            },
            "required": ["applicant_id"],
        },
    },
    {
        "name": "calculate_risk_adjusted_amount",
        "description": (
            "Calculate the risk-adjusted approved amount for the claim. This is the ONLY source "
            "of the approved amount — never estimate or state an amount that did not come from "
            "this tool. Only call this once identity has been verified."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "applicant_id": {"type": "string", "description": "The applicant ID, e.g. APP-1001"},
            },
            "required": ["applicant_id"],
        },
    },
]
