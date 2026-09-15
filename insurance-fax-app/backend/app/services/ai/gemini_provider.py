"""
Google Gemini AI provider.

Handles both claim field extraction and the grounded chat agent.
Every request forces JSON-mode output so the rest of the backend can
rely on a fixed response shape instead of parsing free-form prose.

This is the ONLY file in the backend that imports the Gemini SDK --
everything else talks to the AIProvider interface.
"""

import json
import logging

import google.generativeai as genai

from ...core.exceptions import AIProviderError
from .base import AIChatResult, AIFieldResult, AIProvider

logger = logging.getLogger("app.ai.gemini")

EXTRACTION_PROMPT = """You are an information extraction engine for insurance claim documents.

Extract ONLY the following fields from the document text below. For each field, return the
exact value as it appears in the text, a confidence score between 0 and 1, and the exact
verbatim snippet of text (sourceText) the value was taken from.

Rules:
- If a field is not present in the document, return null for "value", 0 for "confidence", and
  null for "sourceText". NEVER invent or guess a value that is not literally in the text.
- "sourceText" must be an exact substring of the document text (copy it verbatim).
- Return ONLY valid JSON matching this exact shape, with no extra commentary:

{{
  "fields": {{
    "<fieldName>": {{"value": "<string or null>", "confidence": <0-1 number>, "sourceText": "<string or null>"}}
  }}
}}

Fields to extract: {field_names}

Document text:
---
{document_text}
---
"""

CHAT_PROMPT = """{system_prompt}

Claim context (the ONLY information you are allowed to use):
---
{context}
---

Manager question: {question}

Return ONLY valid JSON with no extra commentary, matching this exact shape:
{{
  "found": <true or false>,
  "answer": "<your answer text, or the not-found message if found is false>",
  "sourceField": "<field name this answer came from, or null>",
  "sourcePage": <page number as integer, or null>,
  "sourceText": "<exact snippet from the context that supports the answer, or null>"
}}

Set "found" to false whenever the requested information is not present in the context above.
"""


class GeminiProvider(AIProvider):
    name = "gemini"
    supports_chat = True

    def __init__(self, api_key: str, model_name: str):
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name)

    def _generate_json(self, prompt: str) -> dict:
        try:
            response = self._model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json"),
            )
            return json.loads(response.text)
        except Exception as exc:  # network errors, invalid key, malformed JSON, etc.
            logger.warning("gemini_call_failed: %s", exc)
            raise AIProviderError("The AI provider could not be reached. Falling back to rule-based analysis.") from exc

    def extract_fields(self, document_text: str, field_names: list[str]) -> dict[str, AIFieldResult]:
        prompt = EXTRACTION_PROMPT.format(field_names=", ".join(field_names), document_text=document_text[:60000])
        data = self._generate_json(prompt)
        raw_fields = data.get("fields", {})

        results: dict[str, AIFieldResult] = {}
        for field_name in field_names:
            entry = raw_fields.get(field_name) or {}
            value = entry.get("value")
            results[field_name] = AIFieldResult(
                value=value if value else None,
                confidence=float(entry.get("confidence") or 0.0),
                source_text=entry.get("sourceText"),
            )
        return results

    def chat(self, question: str, context: str, system_prompt: str) -> AIChatResult:
        prompt = CHAT_PROMPT.format(system_prompt=system_prompt, context=context[:60000], question=question)
        data = self._generate_json(prompt)
        return AIChatResult(
            answer=data.get("answer") or "I could not find this information in the analyzed claim documents.",
            found=bool(data.get("found")),
            source_field=data.get("sourceField"),
            source_page=data.get("sourcePage"),
            source_text=data.get("sourceText"),
        )
