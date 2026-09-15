from fastapi import APIRouter

from .routes import chat, claims, dashboard, documents, tts

api_router = APIRouter(prefix="/api")
api_router.include_router(documents.router)
api_router.include_router(claims.router)
api_router.include_router(chat.router)
api_router.include_router(dashboard.router)
api_router.include_router(tts.router)
