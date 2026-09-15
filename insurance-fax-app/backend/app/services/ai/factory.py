"""Picks the configured AI provider. All AI calls in the backend go through here."""

import logging

from ...core.config import Settings
from .base import AIProvider
from .rule_based_provider import RuleBasedProvider

logger = logging.getLogger("app.ai.factory")

_provider_cache: dict[str, AIProvider] = {}


def get_ai_provider(settings: Settings) -> AIProvider:
    if not settings.ai_configured:
        return RuleBasedProvider()

    cache_key = f"{settings.ai_provider}:{settings.ai_model}:{settings.ai_api_key[-6:]}"
    if cache_key in _provider_cache:
        return _provider_cache[cache_key]

    if settings.ai_provider.lower() == "gemini":
        from .gemini_provider import GeminiProvider

        provider: AIProvider = GeminiProvider(api_key=settings.ai_api_key, model_name=settings.ai_model)
    else:
        logger.warning("unknown_ai_provider_falling_back_to_rule_based: %s", settings.ai_provider)
        provider = RuleBasedProvider()

    _provider_cache[cache_key] = provider
    return provider
