"""In-memory store for Discovery assessments, so a stored assessment can
be retrieved later -- e.g. by the Implementation tab when running an
agent simulation against a specific fax."""

import uuid


class DiscoveryRepository:
    def __init__(self):
        self._assessments: dict[str, dict] = {}

    def add(self, assessment: dict) -> dict:
        assessment_id = str(uuid.uuid4())[:8]
        assessment["id"] = assessment_id
        self._assessments[assessment_id] = assessment
        return assessment

    def get(self, assessment_id: str) -> dict | None:
        return self._assessments.get(assessment_id)


discovery_repository = DiscoveryRepository()
