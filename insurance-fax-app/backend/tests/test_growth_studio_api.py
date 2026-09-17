import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


HEALTHCARE_PROCESS = (
    "1. Fax received with patient demographics and diagnosis.\n"
    "2. Clinical reviewer checks the diagnosis against policy criteria.\n"
    "3. Prior authorization decision recorded and sent back to the hospital.\n"
)

VALID_CLAIM_TEXT = (
    "Patient Name: Raj Kumar\nDate of Birth: 12/03/1985\nMember ID: M-24567\n"
    "Insurance Company: Star Health\nPolicy Number: ABC123456\nClaim Number: CLM-2026-4567\n"
    "Hospital Name: City General Hospital\nDoctor Name: Dr. Sharma\nDiagnosis: Acute pancreatitis\n"
    "Admission Date: 12/08/2026\nDischarge Date: 15/08/2026\nTotal Claim Amount: Rs. 85000\n"
)


def make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text, fontsize=10)
    return doc.tobytes()


def test_assess_process_and_retrieve_it(client):
    r = client.post("/api/discovery/assess", json={"process_text": HEALTHCARE_PROCESS})
    assert r.status_code == 200
    body = r.json()
    assert body["domain"] == "healthcare"
    assessment_id = body["id"]

    r2 = client.get(f"/api/discovery/{assessment_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == assessment_id


def test_assess_empty_process_returns_plain_english_error_not_500(client):
    r = client.post("/api/discovery/assess", json={"process_text": "   "})
    assert r.status_code == 400
    body = r.json()
    assert body["success"] is False
    assert "empty" in body["error"]["message"].lower()


def test_get_unknown_assessment_returns_404(client):
    r = client.get("/api/discovery/does-not-exist")
    assert r.status_code == 404


def test_simulate_requires_a_real_fax_and_assessment(client):
    r = client.post("/api/implementation/simulate", json={"fax_id": "nope", "assessment_id": "nope"})
    assert r.status_code == 404


def test_simulate_end_to_end_with_a_real_claim(client):
    upload = client.post("/api/faxes/upload", files={"file": ("claim.pdf", make_pdf(VALID_CLAIM_TEXT), "application/pdf")})
    assert upload.status_code == 200
    fax_id = upload.json()["id"]

    assess = client.post("/api/discovery/assess", json={"process_text": HEALTHCARE_PROCESS})
    assessment_id = assess.json()["id"]

    sim = client.post("/api/implementation/simulate", json={"fax_id": fax_id, "assessment_id": assessment_id})
    assert sim.status_code == 200
    body = sim.json()
    assert body["final_status"] in ("Auto-Approved", "Human Review Required", "Escalate to Human Review")
    assert body["fax_id"] == fax_id


def test_roi_calculate_endpoint(client):
    r = client.post(
        "/api/roi/calculate",
        json={"annual_volume": 200000, "mins_per_request": 12, "automation_pct": 0.75},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["annual_savings"] == 750000


def test_roi_calculate_rejects_invalid_automation_pct(client):
    r = client.post(
        "/api/roi/calculate",
        json={"annual_volume": 200000, "mins_per_request": 12, "automation_pct": 1.5},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["success"] is False


def test_revenue_calculate_endpoint(client):
    r = client.post("/api/revenue/calculate", json={"touchpoints": 5, "agent_count": 4, "domain": "healthcare"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert "managed" in body
