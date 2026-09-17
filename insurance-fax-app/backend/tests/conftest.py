"""
Shared test fixtures.

The automated test suite must never depend on a real (paid, rate-limited,
sometimes slow) AI API call, regardless of what's actually sitting in the
developer's own backend/.env -- a real AI_API_KEY there is for manual/local
use of the running app, not for pytest. Discovered the hard way: once a
working key was configured, the full suite went from ~10s to ~19 minutes
because every route-level test (upload, discovery, chat, simulation) was
silently making real Gemini calls.

This autouse fixture forces AI_API_KEY empty for every test, so
get_ai_provider() always returns the deterministic RuleBasedProvider unless
a test explicitly constructs and injects its own (mocked) AIProvider --
which is exactly what test_chat_service.py, test_discovery.py, and
test_implementation.py already do for the cases that need to exercise
AI-specific behavior.
"""

import pytest

from app.core.config import get_settings
from app.services.ai import factory as ai_factory


@pytest.fixture(autouse=True)
def force_rule_based_ai_provider(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "")
    get_settings.cache_clear()
    ai_factory._provider_cache.clear()
    yield
    get_settings.cache_clear()
    ai_factory._provider_cache.clear()
