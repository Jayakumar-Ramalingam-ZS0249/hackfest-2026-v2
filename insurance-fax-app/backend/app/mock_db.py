"""Eligibility lookup placeholder. Real implementations should query a secured insurer system."""

ELIGIBILITY_DB = {}


def lookup_member(member_number: str):
    """Return eligibility info only when a real record exists in the database."""
    return ELIGIBILITY_DB.get(member_number)
