"""
Text-to-speech synthesis for the AI Manager's spoken responses.

Uses pyttsx3 -- an offline, local OS voice engine (SAPI5 on Windows,
NSSpeechSynthesizer on macOS, espeak on Linux). No external API, no
network call, no credential. This is deliberate: it's what lets the
frontend receive REAL playable audio bytes to pipe through the Web
Audio API for genuine amplitude-driven avatar lip-sync -- the browser's
own SpeechSynthesis API exposes no underlying audio stream, so it
cannot drive a real analyser. Speaks the exact text it is given: never
rewrites, summarizes, or invents speech.
"""

import logging
import os
import sys
import tempfile

import pyttsx3

from ...core.exceptions import AppError

logger = logging.getLogger("app.tts")

MAX_TTS_CHARS = 2000


class TTSError(AppError):
    status_code = 502
    code = "TTS_ERROR"


def _synthesize_to_file(text: str, path: str) -> None:
    # pyttsx3 drives SAPI5 through COM on Windows. Each call may run on a
    # fresh thread-pool worker thread with no COM apartment initialized,
    # which fails with "CoInitialize has not been called" -- so this
    # thread must initialize its own COM apartment before using pyttsx3
    # and tear it down afterward. Only relevant on Windows.
    pythoncom = None
    if sys.platform == "win32":
        import pythoncom as _pythoncom

        pythoncom = _pythoncom
        pythoncom.CoInitialize()
    try:
        engine = pyttsx3.init()
        try:
            engine.save_to_file(text, path)
            engine.runAndWait()
        finally:
            engine.stop()
    finally:
        if pythoncom is not None:
            pythoncom.CoUninitialize()


def synthesize_speech(text: str) -> bytes:
    """Synthesizes `text` verbatim to WAV bytes.

    Blocking/CPU-bound -- callers on an async request path must run this
    via a thread pool (see routes/tts.py).
    """
    clean_text = (text or "").strip()
    if not clean_text:
        raise TTSError("No text was provided to synthesize.", code="TTS_EMPTY_TEXT", status_code=400)
    clean_text = clean_text[:MAX_TTS_CHARS]

    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        _synthesize_to_file(clean_text, path)
        with open(path, "rb") as f:
            audio_bytes = f.read()
        if not audio_bytes:
            raise TTSError("The text-to-speech engine produced no audio.", code="TTS_EMPTY_OUTPUT")
        return audio_bytes
    except TTSError:
        raise
    except Exception as exc:
        logger.warning("tts_synthesis_failed: %s", exc)
        raise TTSError("The text-to-speech engine is unavailable on this server.") from exc
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
