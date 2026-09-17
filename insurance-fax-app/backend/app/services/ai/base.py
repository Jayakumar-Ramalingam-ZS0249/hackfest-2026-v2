"""
AI provider abstraction.

Every place in the backend that needs an AI call (claim field
extraction, the chat agent) goes through this interface instead of
calling an SDK directly. This is what lets AI_PROVIDER be swapped
(Gemini today, OpenAI/Anthropic/local later) without touching the
extraction or chat services.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIFieldResult:
    value: str | None
    confidence: float
    source_text: str | None


@dataclass
class AIChatResult:
    answer: str
    found: bool
    source_field: str | None = None
    source_page: int | None = None
    source_text: str | None = None


class AIProvider(ABC):
    """Base class for all AI providers. Never called directly from routers."""

    name: str = "base"
    supports_chat: bool = False

    @abstractmethod
    def extract_fields(self, document_text: str, field_names: list[str]) -> dict[str, AIFieldResult]:
        """Return a structured value/confidence/sourceText per requested field.

        Must NEVER invent a value for a field that isn't actually present in
        document_text -- return None for anything it can't find.
        """
        raise NotImplementedError

    def chat(self, question: str, context: str, system_prompt: str) -> AIChatResult:
        raise NotImplementedError(f"{self.name} does not support chat")

    def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        """Generic structured-JSON drafting for features beyond field
        extraction/chat (discovery assessments, agent-simulation drafts).

        Callers must NEVER trust this output for a compliance-relevant
        decision without an independent code-level check -- see
        agents/discovery.py's whitelist filter and
        agents/implementation.py's exception-flag overrides for the
        enforcement side of that rule. The LLM only drafts; code decides.
        """
        raise NotImplementedError(f"{self.name} does not support generate_json")
