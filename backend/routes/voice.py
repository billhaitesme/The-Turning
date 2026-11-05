"""Voice — the runtime's ears and mouth (voice/vision slice, 2026-11-05).

Both run LOCALLY on CPU: no network, no breaker, nothing leaves the machine.

  ears  — POST /voice/transcribe: audio bytes in (webm/wav/ogg), text out. faster-whisper
          (VOICE_STT_MODEL, default "base", int8). The transcript is shown to the operator as
          their own message — speech is input, not interpretation.
  mouth — POST /voice/speak: text in, WAV out. Kokoro-82M via ONNX (no torch), voice
          VOICE_TTS_VOICE (default bm_fable — the house voice family). Model files live at
          backend/models/voice/ and are fetched at build time, never by the runtime.

Engines initialize lazily on first use and report plainly when their files are missing.
"""
from __future__ import annotations

import io
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/voice", tags=["voice"])

VOICE_MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "voice"
MAX_AUDIO_BYTES = 15_000_000
MAX_SPEAK_CHARS = 1200

_lock = threading.Lock()
_whisper_model: Optional[Any] = None
_kokoro_engine: Optional[Any] = None


def _get_whisper():
    global _whisper_model
    with _lock:
        if _whisper_model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise HTTPException(status_code=503,
                                    detail="Ears unavailable: faster-whisper is not installed.") from exc
            size = os.getenv("VOICE_STT_MODEL", "base")
            # CPU on purpose: the ears must work while the GPU trains or thinks.
            _whisper_model = WhisperModel(size, device="cpu", compute_type="int8")
        return _whisper_model


def _get_kokoro():
    global _kokoro_engine
    with _lock:
        if _kokoro_engine is None:
            try:
                from kokoro_onnx import Kokoro
            except ImportError as exc:
                raise HTTPException(status_code=503,
                                    detail="Mouth unavailable: kokoro-onnx is not installed.") from exc
            model_path = VOICE_MODEL_DIR / "kokoro-v1.0.onnx"
            voices_path = VOICE_MODEL_DIR / "voices-v1.0.bin"
            if not model_path.exists() or not voices_path.exists():
                raise HTTPException(status_code=503,
                                    detail=f"Mouth unavailable: Kokoro model files missing under "
                                           f"{VOICE_MODEL_DIR} (kokoro-v1.0.onnx + voices-v1.0.bin).")
            try:
                _kokoro_engine = Kokoro(str(model_path), str(voices_path))
            except Exception as exc:  # noqa: BLE001 — a partial/corrupt download reports plainly
                raise HTTPException(status_code=503,
                                    detail="Mouth unavailable: Kokoro model files unreadable "
                                           f"(incomplete download?): {exc}") from exc
        return _kokoro_engine


@router.get("/status")
def voice_status() -> Dict[str, Any]:
    return {
        "stt_model": os.getenv("VOICE_STT_MODEL", "base"),
        "tts_voice": os.getenv("VOICE_TTS_VOICE", "bm_fable"),
        "tts_files_present": (VOICE_MODEL_DIR / "kokoro-v1.0.onnx").exists()
                             and (VOICE_MODEL_DIR / "voices-v1.0.bin").exists(),
        "local_only": True,
    }


@router.post("/transcribe")
async def transcribe(request: Request) -> Dict[str, Any]:
    """Raw audio bytes in the body (the mic recorder's blob); the transcript out."""
    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=422, detail="No audio received.")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=422, detail="Audio exceeds the 15 MB cap.")
    model = _get_whisper()
    try:
        segments, info = model.transcribe(io.BytesIO(audio), beam_size=1, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
    except Exception as exc:  # noqa: BLE001 — a failed transcription is a reported state
        raise HTTPException(status_code=422, detail=f"Could not transcribe: {exc}") from exc
    return {"text": text, "language": getattr(info, "language", None),
            "duration_seconds": round(float(getattr(info, "duration", 0.0)), 2)}


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_SPEAK_CHARS)
    voice: Optional[str] = Field(default=None, max_length=40)
    speed: float = Field(default=1.0, ge=0.5, le=1.6)


@router.post("/speak")
def speak(req: SpeakRequest) -> Response:
    engine = _get_kokoro()
    voice = req.voice or os.getenv("VOICE_TTS_VOICE", "bm_fable")
    try:
        samples, sample_rate = engine.create(req.text, voice=voice, speed=req.speed, lang="en-gb")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Could not speak: {exc}") from exc
    import soundfile as sf
    buffer = io.BytesIO()
    sf.write(buffer, samples, sample_rate, format="WAV")
    return Response(content=buffer.getvalue(), media_type="audio/wav")
