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
    "Patient Name: Dana Analytics\nDate of Birth: 01/01/1990\nMember ID: M-99001\n"
    "Insurance Company: Analytics Test Insurer\nPolicy Number: ANL123456\nClaim Number: CLM-ANL-0001\n"
    "Hospital Name: Analytics General Hospital\nDoctor Name: Dr. Metrics\nDiagnosis: Test condition\n"
    "Admission Date: 01/02/2026\nDischarge Date: 03/02/2026\nTotal Claim Amount: Rs. 42000\n"
)

IRRELEVANT_TEXT = "Weekly newsletter. Big summer sale. 40 percent off everything today only."


def _upload(client, text: str, filename: str = "doc.pdf"):
    return client.post(
        "/api/faxes/upload", files={"file": (filename, make_pdf(text), "application/pdf")}
    )


def test_overview_reflects_a_real_uploaded_claim(client):
    upload = _upload(client, VALID_CLAIM_TEXT, "analytics_valid.pdf")
    assert upload.status_code == 200
    claim_id = upload.json()["id"]

    r = client.get("/api/dashboard/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    data = body["data"]

    assert data["summary"]["totalClaims"] >= 1
    assert data["financial"]["available"] is True
    assert data["financial"]["totalClaimValue"] >= 42000

    provider_names = [p["provider"] for p in data["insuranceProviders"]]
    assert "Analytics Test Insurer" in provider_names

    activity_claim_ids = [a["claimId"] for a in data["recentActivity"]]
    assert claim_id in activity_claim_ids


def test_overview_status_filter_only_returns_matching_claims(client):
    _upload(client, IRRELEVANT_TEXT, "analytics_invalid.pdf")

    r = client.get("/api/dashboard/overview", params={"status": "invalid"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["summary"]["totalClaims"] == data["summary"]["invalid"]
    assert data["summary"]["resolved"] == 0
    assert data["summary"]["pendingReview"] == 0


def test_overview_rejects_malformed_date(client):
    r = client.get("/api/dashboard/overview", params={"from": "not-a-date"})
    assert r.status_code == 400
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_DATE"


def test_providers_endpoint_lists_distinct_companies(client):
    _upload(client, VALID_CLAIM_TEXT, "analytics_providers.pdf")

    r = client.get("/api/dashboard/providers")
    assert r.status_code == 200
    assert "Analytics Test Insurer" in r.json()


def test_attention_summary_lists_real_invalid_claim(client):
    upload = _upload(client, IRRELEVANT_TEXT, "analytics_attention.pdf")
    claim_id = upload.json()["id"]

    r = client.get("/api/dashboard/attention-summary")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    claim_ids = [item["claimId"] for item in body["items"]]
    assert claim_id in claim_ids


def test_export_returns_csv_with_header_row(client):
    _upload(client, VALID_CLAIM_TEXT, "analytics_export.pdf")

    r = client.get("/api/dashboard/export")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "Claim ID" in r.text
    assert "Analytics Test Insurer" in r.text
