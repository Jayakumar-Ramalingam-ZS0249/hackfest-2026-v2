import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_tts_synthesizes_real_playable_audio(client):
    r = client.post("/api/ai/tts", json={"text": "The approved claim amount is eighty four thousand rupees."})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    # A real WAV header starts with "RIFF"...."WAVE" -- not an empty/fake stub.
    assert r.content[:4] == b"RIFF"
    assert r.content[8:12] == b"WAVE"
    assert len(r.content) > 1000


def test_tts_speaks_the_exact_text_length_scales_with_input(client):
    short = client.post("/api/ai/tts", json={"text": "Hi."})
    long = client.post(
        "/api/ai/tts",
        json={"text": "This is a considerably longer sentence than the very short one used above."},
    )
    assert short.status_code == 200
    assert long.status_code == 200
    # Longer text should produce meaningfully more audio, not identical/fake output.
    assert len(long.content) > len(short.content)


def test_tts_rejects_empty_text(client):
    r = client.post("/api/ai/tts", json={"text": ""})
    assert r.status_code in (400, 422)
