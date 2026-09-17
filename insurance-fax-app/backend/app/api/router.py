from fastapi import APIRouter

from .routes import chat, claims, dashboard, discovery, documents, revenue, roi, simulation, tts

api_router = APIRouter(prefix="/api")
api_router.include_router(documents.router)
api_router.include_router(claims.router)
api_router.include_router(chat.router)
api_router.include_router(dashboard.router)
api_router.include_router(tts.router)
api_router.include_router(discovery.router)
api_router.include_router(simulation.router)
api_router.include_router(roi.router)
api_router.include_router(revenue.router)
