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
    "Patient Name: Raj Kumar\nDate of Birth: 12/03/1985\nMember ID: M-24567\n"
    "Insurance Company: Star Health\nPolicy Number: ABC123456\nClaim Number: CLM-2026-4567\n"
    "Hospital Name: City General Hospital\nDoctor Name: Dr. Sharma\nDiagnosis: Acute pancreatitis\n"
    "Admission Date: 12/08/2026\nDischarge Date: 15/08/2026\nTotal Claim Amount: Rs. 85000\n"
)

IRRELEVANT_TEXT = "Welcome to our newsletter. Summer sale starts today. Buy our products and save 40 percent."


def test_health_check(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_upload_empty_file_is_rejected(client):
    r = client.post("/api/faxes/upload", files={"file": ("empty.pdf", b"", "application/pdf")})
    assert r.status_code == 400
    body = r.json()
    assert body["success"] is False
    assert "code" in body["error"]


def test_upload_non_pdf_extension_is_rejected(client):
    r = client.post("/api/faxes/upload", files={"file": ("claim.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_upload_valid_claim_pdf_extracts_fields_with_no_fabrication(client):
    r = client.post("/api/faxes/upload", files={"file": ("claim.pdf", make_pdf(VALID_CLAIM_TEXT), "application/pdf")})
    assert r.status_code == 200
    record = r.json()

    assert record["status"] in ("auto_filled", "needs_review")
    assert record["document"]["matchScore"] > 60
    assert record["fields"]["patientName"]["value"] == "Raj Kumar"
    assert record["fields"]["patientName"]["verificationStatus"] == "VERIFIED"


def test_upload_irrelevant_pdf_is_rejected_with_zero_fields(client):
    r = client.post("/api/faxes/upload", files={"file": ("newsletter.pdf", make_pdf(IRRELEVANT_TEXT), "application/pdf")})
    assert r.status_code == 200
    record = r.json()

    assert record["status"] == "invalid"
    assert record["document"]["matchScore"] <= 25
    assert record["fields"] == {}, "an invalid document must never contain fabricated extracted fields"


def test_claims_list_and_get_roundtrip(client):
    upload = client.post("/api/faxes/upload", files={"file": ("claim.pdf", make_pdf(VALID_CLAIM_TEXT), "application/pdf")})
    claim_id = upload.json()["id"]

    listing = client.get("/api/claims")
    assert listing.status_code == 200
    assert any(c["id"] == claim_id for c in listing.json())

    detail = client.get(f"/api/claims/{claim_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == claim_id


def test_get_unknown_claim_returns_structured_404(client):
    r = client.get("/api/claims/does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


def test_chat_on_invalid_document_is_rejected(client):
    upload = client.post("/api/faxes/upload", files={"file": ("newsletter.pdf", make_pdf(IRRELEVANT_TEXT), "application/pdf")})
    claim_id = upload.json()["id"]

    r = client.post(f"/api/claims/{claim_id}/chat", json={"message": "What is the claim amount?"})
    assert r.status_code == 422


def test_chat_without_ai_provider_never_hallucinates(client):
    upload = client.post("/api/faxes/upload", files={"file": ("claim.pdf", make_pdf(VALID_CLAIM_TEXT), "application/pdf")})
    claim_id = upload.json()["id"]

    r = client.post(f"/api/claims/{claim_id}/chat", json={"message": "What is the patient's father's name?"})
    assert r.status_code == 200
    body = r.json()
    assert "father" not in body["answer"].lower()


def test_dashboard_statistics_reflect_real_uploads_not_fake_numbers(client):
    before = client.get("/api/dashboard/statistics").json()
    client.post("/api/faxes/upload", files={"file": ("claim.pdf", make_pdf(VALID_CLAIM_TEXT), "application/pdf")})
    after = client.get("/api/dashboard/statistics").json()

    assert after["totalClaims"] == before["totalClaims"] + 1
