"""Seed data for the in-memory store. 20 mock applicants spanning every status,
verification outcome, and risk profile the demo needs to tell a complete story:
clean approvals (full and partially reduced), identity-verification rejections,
fraud-flagged escalations, a policy-compliance escalation, and a handful of
already-decided historical claims so the dashboard KPIs have something to show
the moment the app starts.

Timestamps are computed relative to import time (not hardcoded dates) so the
demo always looks fresh, whenever it's run.
"""

from datetime import datetime, timedelta, timezone
from typing import List

from app.models.schemas import Applicant

_NOW = datetime.now(timezone.utc)


def _ago(days: float = 0, hours: float = 0) -> datetime:
    return _NOW - timedelta(days=days, hours=hours)


# Each tuple: (id, name, aadhar, aadhar_ok, pan, pan_ok, claim_type, amount,
#              tenure_years, prior_claims, risk_score, status,
#              approved_amount, decided_by, decision_notes,
#              submitted_at, last_updated)
_RAW = [
    (
        "APP-1001", "Ravi Kumar", "XXXX-XXXX-4521", True, "ABCPK4321Q", True,
        "Hospitalization", 250000, 3, 1, 0.42, "pending_review",
        None, None, None, _ago(days=3), _ago(days=3),
    ),
    (
        "APP-1002", "Sunita Reddy", "XXXX-XXXX-7788", True, "BFXPR7788L", True,
        "Surgery", 180000, 5, 0, 0.30, "pending_review",
        None, None, None, _ago(days=2), _ago(days=2),
    ),
    (
        "APP-1003", "Arjun Mehta", "XXXX-XXXX-5567", True, "CMNPA5567H", True,
        "Hospitalization", 220000, 1, 3, 0.75, "pending_review",
        None, None, None, _ago(days=1), _ago(days=1),
    ),
    (
        "APP-1004", "Priya Nair", "XXXX-XXXX-1123", True, "DQZPN1123K", False,
        "Critical Illness", 480000, 2, 0, 0.55, "pending_review",
        None, None, None, _ago(hours=6), _ago(hours=6),
    ),
    (
        "APP-1005", "Karan Singh", "XXXX-XXXX-9911", True, "EFTPS9911B", True,
        "Outpatient", 20000, 6, 0, 0.10, "approved",
        20000, "Anita Desai", "Clean profile, approved at full requested amount.",
        _ago(days=3), _ago(hours=2),
    ),
    (
        "APP-1006", "Meera Iyer", "XXXX-XXXX-3345", False, "GHUPI3345M", True,
        "Accident", 350000, 2, 2, 0.60, "pending_review",
        None, None, None, _ago(days=1), _ago(days=1),
    ),
    (
        "APP-1007", "Vikram Rao", "XXXX-XXXX-6654", True, "HIJPR6654N", True,
        "Maternity", 120000, 4, 1, 0.30, "approved",
        120000, "Rahul Verma", "Approved at full amount; tenure and claim history both clean.",
        _ago(days=4), _ago(hours=5),
    ),
    (
        "APP-1008", "Ananya Das", "XXXX-XXXX-2298", True, "JKLPD2298P", True,
        "Hospitalization", 500000, 1, 4, 0.88, "needs_human_review",
        None, None, None, _ago(days=2), _ago(days=1),
    ),
    (
        "APP-1009", "Rohit Sharma", "XXXX-XXXX-7712", True, "KLMPS7712Q", True,
        "Surgery", 150000, 0, 0, 0.25, "pending_review",
        None, None, None, _ago(hours=5), _ago(hours=5),
    ),
    (
        "APP-1010", "Divya Menon", "XXXX-XXXX-4409", True, "LMNPM4409R", True,
        "Outpatient", 45000, 5, 0, 0.22, "rejected",
        None, "Anita Desai", "Duplicate claim identified during manual audit.",
        _ago(days=2), _ago(hours=3),
    ),
    (
        "APP-1011", "Suresh Pillai", "XXXX-XXXX-8834", False, "MNOPP8834S", False,
        "Hospitalization", 210000, 1, 2, 0.65, "pending_review",
        None, None, None, _ago(hours=12), _ago(hours=12),
    ),
    (
        "APP-1012", "Kavya Krishnan", "XXXX-XXXX-2256", True, "NOPPK2256T", True,
        "Critical Illness", 400000, 7, 0, 0.33, "pending_review",
        None, None, None, _ago(hours=4), _ago(hours=4),
    ),
    (
        "APP-1013", "Aditya Joshi", "XXXX-XXXX-5578", True, "OPQPJ5578U", True,
        "Accident", 60000, 2, 0, 0.15, "approved",
        60000, "Sneha Kulkarni", "Low risk, approved at full amount.",
        _ago(days=5), _ago(days=1),
    ),
    (
        "APP-1014", "Neha Kapoor", "XXXX-XXXX-9987", True, "PQRPK9987V", True,
        "Maternity", 150000, 3, 1, 0.40, "pending_review",
        None, None, None, _ago(days=2), _ago(days=2),
    ),
    (
        "APP-1015", "Manoj Tiwari", "XXXX-XXXX-3312", True, "QRSPT3312W", True,
        "Hospitalization", 320000, 2, 3, 0.70, "needs_human_review",
        None, None, None, _ago(days=3), _ago(days=1),
    ),
    (
        "APP-1016", "Pooja Verma", "XXXX-XXXX-6645", True, "RSTPV6645X", False,
        "Surgery", 90000, 4, 0, 0.25, "pending_review",
        None, None, None, _ago(hours=8), _ago(hours=8),
    ),
    (
        "APP-1017", "Sanjay Gupta", "XXXX-XXXX-1189", True, "STUPG1189Y", True,
        "Outpatient", 30000, 8, 0, 0.05, "approved",
        30000, "Rahul Verma", "Long-tenured, spotless history — approved at full amount.",
        _ago(days=6), _ago(days=2),
    ),
    (
        "APP-1018", "Ritu Chawla", "XXXX-XXXX-4423", True, "TUVPC4423Z", True,
        "Hospitalization", 275000, 2, 2, 0.52, "rejected",
        None, "Sneha Kulkarni", "Claim withdrawn by applicant.",
        _ago(days=4), _ago(days=1),
    ),
    (
        "APP-1019", "Farhan Ali", "XXXX-XXXX-7756", True, "UVWPA7756A", True,
        "Critical Illness", 460000, 1, 5, 0.91, "needs_human_review",
        None, None, None, _ago(days=1), _ago(hours=10),
    ),
    (
        "APP-1020", "Ishita Bose", "XXXX-XXXX-2287", True, "VWXPB2287B", True,
        "Accident", 75000, 5, 0, 0.20, "pending_review",
        None, None, None, _ago(hours=1), _ago(hours=1),
    ),
]


def build_seed_applicants() -> List[Applicant]:
    applicants = []
    for row in _RAW:
        (
            applicant_id, name, aadhar, aadhar_ok, pan, pan_ok, claim_type, amount,
            tenure, prior_claims, risk, status, approved_amount, decided_by,
            notes, submitted_at, last_updated,
        ) = row
        applicants.append(
            Applicant(
                applicant_id=applicant_id,
                name=name,
                aadhar_number=aadhar,
                aadhar_verified=aadhar_ok,
                pan_number=pan,
                pan_verified=pan_ok,
                claim_type=claim_type,
                claim_amount_requested=float(amount),
                policy_tenure_years=tenure,
                prior_claims_count=prior_claims,
                risk_score=risk,
                status=status,
                approved_amount=float(approved_amount) if approved_amount is not None else None,
                ai_recommendation=None,
                submitted_at=submitted_at,
                last_updated=last_updated,
                decided_by=decided_by,
                decision_notes=notes,
            )
        )
    return applicants
