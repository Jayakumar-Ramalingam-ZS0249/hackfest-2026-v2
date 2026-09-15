import time

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text, fontsize=10)
    return doc.tobytes()


VALID_CLAIM_TEXT = (
    "Patient Name: Progress Test\nDate of Birth: 01/01/1990\nMember ID: M-PRG001\n"
    "Insurance Company: Progress Insurer\nPolicy Number: PRG123456\nClaim Number: CLM-PRG-0001\n"
    "Hospital Name: Progress General Hospital\nDoctor Name: Dr. Progress\nDiagnosis: Test condition\n"
    "Admission Date: 01/02/2026\nDischarge Date: 03/02/2026\nTotal Claim Amount: Rs. 15000\n"
)


def _poll_until_done(client, job_id: str, timeout_seconds: float = 10.0) -> dict:
    deadline = time.time() + timeout_seconds
    seen_stages = []
    while time.time() < deadline:
        r = client.get(f"/api/documents/upload-status/{job_id}")
        assert r.status_code == 200
        status = r.json()
        seen_stages.append(status["stage"])
        if status["done"]:
            status["_seen_stages"] = seen_stages
            return status
        time.sleep(0.05)
    raise AssertionError(f"Upload job {job_id} did not complete within {timeout_seconds}s; stages seen: {seen_stages}")


def test_async_upload_reports_real_stage_progress_and_completes(client):
    upload = client.post(
        "/api/faxes/upload-async", files={"file": ("progress.pdf", make_pdf(VALID_CLAIM_TEXT), "application/pdf")}
    )
    assert upload.status_code == 200
    job_id = upload.json()["jobId"]

    status = _poll_until_done(client, job_id)
    assert status["error"] is None
    assert status["result"] is not None
    assert status["result"]["fields"]["patientName"]["value"] == "Progress Test"
    assert status["percent"] == 100

    # Real, distinct pipeline stages were actually reported -- not a single jump.
    distinct_stages = set(status["_seen_stages"])
    assert len(distinct_stages) >= 2

    # The claim must also be retrievable through the normal claim endpoints.
    claim_id = status["result"]["id"]
    r = client.get(f"/api/claims/{claim_id}")
    assert r.status_code == 200


def test_unknown_upload_job_returns_404(client):
    r = client.get("/api/documents/upload-status/does-not-exist")
    assert r.status_code == 404
