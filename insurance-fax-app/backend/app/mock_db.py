"""
Mock eligibility / patient database.

In production this file is replaced by a real call to the existing
eligibility API / patient database (see LLD section 3 - Eligibility
match agent). For this MVP we keep a small in-memory dictionary keyed
by member number so the pipeline has something real to look up.
"""

ELIGIBILITY_DB = {
    "MRN-8849-X": {
        "client": "Metro Health Alliance",
        "client_code": "MHA-01",
        "plan": "PPO Gold",
        "plan_code": "PPO-G",
        "group_no": "GRP-4471",
        "eligibility_status": "Active",
        "eligibility_start_date": "2024-01-01",
        "eligibility_end_date": "2026-12-31",
    },
    "MRN-1120-A": {
        "client": "Springfield Care Network",
        "client_code": "SCN-02",
        "plan": "HMO Silver",
        "plan_code": "HMO-S",
        "group_no": "GRP-1029",
        "eligibility_status": "Active",
        "eligibility_start_date": "2023-06-01",
        "eligibility_end_date": "2025-06-01",
    },
}


def lookup_member(member_number: str):
    """Look up eligibility info for a given member number.

    Returns None if the member is not found in the mock DB. In the real
    system this would query the live eligibility API and could raise
    a "no match" flag that forces a human review regardless of OCR
    confidence.
    """
    return ELIGIBILITY_DB.get(member_number)
