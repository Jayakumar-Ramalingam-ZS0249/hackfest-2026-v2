"""
In-memory claim repository.

Kept behind this interface (rather than routers/services touching a
module-level dict directly) specifically so it can be swapped for a
real PostgreSQL-backed repository later without changing any service
or route code -- persistence stays in-memory for this pass per
project decision (no Postgres instance available yet).
"""

from ..core.exceptions import NotFoundError


class ClaimRepository:
    def __init__(self):
        self._claims: dict[str, dict] = {}
        self._audit_log: list[dict] = []

    def add(self, record: dict) -> dict:
        self._claims[record["id"]] = record
        return record

    def get(self, claim_id: str) -> dict:
        record = self._claims.get(claim_id)
        if not record:
            raise NotFoundError(f"Claim '{claim_id}' was not found.")
        return record

    def get_or_none(self, claim_id: str) -> dict | None:
        return self._claims.get(claim_id)

    def list_all(self, include_deleted: bool = False) -> list[dict]:
        claims = list(self._claims.values())
        if include_deleted:
            return claims
        return [c for c in claims if not c.get("deleted")]

    def list_deleted(self) -> list[dict]:
        return [c for c in self._claims.values() if c.get("deleted")]

    def update(self, claim_id: str, record: dict) -> dict:
        self._claims[claim_id] = record
        return record

    def append_audit(self, entry: dict) -> None:
        self._audit_log.append(entry)

    def get_audit_log(self, claim_id: str) -> list[dict]:
        return [entry for entry in self._audit_log if entry.get("fax_id") == claim_id or entry.get("claim_id") == claim_id]

    def list_audit_log(self) -> list[dict]:
        """Every audit entry across every claim, most recent first."""
        return sorted(self._audit_log, key=lambda e: e.get("timestamp") or "", reverse=True)

    def statistics(self) -> dict:
        claims = self.list_all()
        total = len(claims)
        by_status = {"resolved": 0, "needs_review": 0, "invalid": 0, "auto_filled": 0}
        confidences = []
        for c in claims:
            status = c.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            if c.get("overall_confidence") is not None:
                confidences.append(c["overall_confidence"])

        return {
            "totalClaims": total,
            "resolved": by_status.get("resolved", 0),
            "needsReview": by_status.get("needs_review", 0),
            "invalidDocuments": by_status.get("invalid", 0),
            "autoFilled": by_status.get("auto_filled", 0),
            "deleted": len(self.list_deleted()),
            "averageConfidence": round(sum(confidences) / len(confidences), 1) if confidences else 0,
        }


# Process-wide singleton: mirrors the previous module-level FAXES dict,
# just accessed through a repository interface instead of directly.
claim_repository = ClaimRepository()
