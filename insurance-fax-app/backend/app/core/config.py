"""
Centralized application configuration.

Everything that used to be a hardcoded constant scattered across the
codebase (max upload size, confidence thresholds, AI provider choice)
lives here instead, read once from environment variables. See
backend/.env.example for the full list of supported variables.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"

    # --- AI provider ---
    # "gemini" uses Google Gemini when AI_API_KEY is set; any other value
    # (or a missing key) makes the app fall back to the deterministic
    # rule-based extractor so the app keeps working with zero external
    # dependencies, exactly like the original MVP.
    ai_provider: str = "gemini"
    ai_model: str = "gemini-2.5-flash"
    ai_api_key: str = ""

    # --- Uploads ---
    max_file_size_mb: int = 10

    # --- Document relevance thresholds (0-100 match score) ---
    invalid_match_threshold: int = 25
    review_match_threshold: int = 60

    # --- Field confidence thresholds (0-1) ---
    low_confidence_threshold: float = 0.70

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_api_key) and self.ai_provider.lower() == "gemini"


@lru_cache
def get_settings() -> Settings:
    return Settings()
