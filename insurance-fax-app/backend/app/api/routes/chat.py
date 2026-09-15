"""
AI Claim Assistant (chat) endpoints.

Every request is scoped to one claim_id and only ever reads that
claim's own extracted fields/document text -- there is no
cross-claim context building, so one manager's question can't leak
another claim's data even without a full auth layer in front of it
(see the architecture report for the auth gap that still needs to be
closed before this is exposed to multiple untrusted users).
"""

import time
import uuid

from fastapi import APIRouter

from ...core.config import get_settings
from ...core.exceptions import DocumentNotRelevantError
from ...repositories.chat_repository import chat_repository
from ...repositories.claim_repository import claim_repository
from ...schemas.chat import ChatMessageResponse, ChatRequest, ChatResponse, ChatSourceResponse
from ...services.ai.factory import get_ai_provider
from ...services.chat.chat_service import ChatService, build_quick_actions
from ...services.extraction.claim_extraction_service import ExtractedField

router = APIRouter(tags=["chat"])


def _record_to_extracted_fields(record: dict) -> dict[str, ExtractedField]:
    from ...services.extraction.claim_extraction_service import ConflictCandidate

    fields: dict[str, ExtractedField] = {}
    for name, data in (record.get("fields") or {}).items():
        conflicts = [ConflictCandidate(page=c["page"], value=c["value"]) for c in data.get("conflicts", [])]
        fields[name] = ExtractedField(
            field_name=name,
            value=data.get("value"),
            confidence=data.get("confidence", 0),
            status=data.get("validationStatus", "not_found"),
            legacy_status=data.get("status", "not_found"),
            page=data.get("page"),
            source_text=data.get("sourceText"),
            verification_status=data.get("verificationStatus", "NOT_APPLICABLE"),
            conflicts=conflicts,
            manager_verified=bool(data.get("managerVerified")),
        )
    return fields


@router.post("/claims/{claim_id}/chat", response_model=ChatResponse)
def send_chat_message(claim_id: str, payload: ChatRequest):
    record = claim_repository.get(claim_id)
    if record["status"] == "invalid":
        raise DocumentNotRelevantError("This document was rejected as not relevant and has no analyzed data to chat about.")

    fields = _record_to_extracted_fields(record)
    pages = record.get("pages") or [record.get("raw_text", "")]
    settings = get_settings()
    ai_provider = get_ai_provider(settings)

    answer, sources, options = ChatService.ask(
        question=payload.message, fields=fields, pages=pages, full_text=record.get("raw_text", ""), ai_provider=ai_provider
    )

    conversation_id = payload.conversationId or str(uuid.uuid4())[:8]
    message_record = {
        "id": str(uuid.uuid4())[:8],
        "claim_id": claim_id,
        "conversation_id": conversation_id,
        "question": payload.message,
        "answer": answer,
        "sources": [{"field": s.field, "page": s.page, "sourceText": s.source_text} for s in sources],
        "clarification_options": options,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    chat_repository.add_message(claim_id, message_record)
    claim_repository.append_audit(
        {"fax_id": claim_id, "claim_id": claim_id, "action": "chat_question_asked", "timestamp": message_record["created_at"]}
    )

    return ChatResponse(
        answer=answer,
        sources=[ChatSourceResponse(field=s.field, page=s.page, sourceText=s.source_text) for s in sources],
        conversationId=conversation_id,
        clarificationOptions=options,
    )


@router.get("/claims/{claim_id}/chat")
def get_chat_history(claim_id: str):
    claim_repository.get(claim_id)
    history = chat_repository.get_history(claim_id)
    return [
        ChatMessageResponse(
            id=m["id"],
            question=m["question"],
            answer=m["answer"],
            sources=[ChatSourceResponse(**s) for s in m["sources"]],
            createdAt=m["created_at"],
            clarificationOptions=m.get("clarification_options", []),
        )
        for m in history
    ]


@router.post("/claims/{claim_id}/chat/new")
def start_new_chat(claim_id: str):
    claim_repository.get(claim_id)
    chat_repository.clear(claim_id)
    return {"success": True, "conversationId": str(uuid.uuid4())[:8]}


@router.get("/claims/{claim_id}/chat/quick-actions")
def get_quick_actions(claim_id: str):
    record = claim_repository.get(claim_id)
    fields = _record_to_extracted_fields(record)
    return {"actions": build_quick_actions(fields)}
