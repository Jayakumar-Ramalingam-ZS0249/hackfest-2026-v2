"""
Text-to-speech endpoint.

Its own thin router since it has nothing to do with claim data -- it
just speaks whatever text it's given (the AI Manager's own response
text, never anything else). Kept separate from chat.py to keep the
grounded-chat pipeline and the speech-synthesis pipeline independently
testable and swappable.
"""

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from ...services.tts.tts_service import synthesize_speech

router = APIRouter(tags=["tts"])


class TtsRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


@router.post("/ai/tts")
async def synthesize(payload: TtsRequest):
    audio_bytes = await run_in_threadpool(synthesize_speech, payload.text)
    return Response(content=audio_bytes, media_type="audio/wav")
