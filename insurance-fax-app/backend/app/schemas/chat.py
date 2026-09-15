from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversationId: str | None = None


class ChatSourceResponse(BaseModel):
    field: str | None = None
    page: int | None = None
    sourceText: str | None = None


class ChatMessageResponse(BaseModel):
    id: str
    question: str
    answer: str
    sources: list[ChatSourceResponse]
    createdAt: str
    clarificationOptions: list[str] = []


class ChatResponse(BaseModel):
    success: bool = True
    answer: str
    sources: list[ChatSourceResponse]
    conversationId: str
    clarificationOptions: list[str] = []
