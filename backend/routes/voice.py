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

from services import voice_setting

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


def _decode_to_16k_mono(audio: bytes):
    """Any container PyAV reads (webm/opus from the browser, wav, ogg, m4a) -> float32 16 kHz mono.

    Decoded here rather than by faster-whisper's own decode_audio: that helper passes
    av.open(..., metadata_errors=...), a keyword PyAV 19 no longer accepts, so every
    transcription failed with "open() got an unexpected keyword argument" (found 2026-11-06).
    """
    import av
    import numpy as np

    chunks = []
    with av.open(io.BytesIO(audio), mode="r") as container:
        stream = next((s for s in container.streams if s.type == "audio"), None)
        if stream is None:
            raise ValueError("no audio stream in the recording")
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray().reshape(-1))
        for out in resampler.resample(None):  # flush
            chunks.append(out.to_ndarray().reshape(-1))
    if not chunks:
        raise ValueError("the recording decoded to silence (zero samples)")
    return np.concatenate(chunks).astype(np.float32) / 32768.0


@router.get("/status")
def voice_status() -> Dict[str, Any]:
    return {
        "stt_model": os.getenv("VOICE_STT_MODEL", "base"),
        "tts_voice": voice_setting.current_voice(),
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
        samples = _decode_to_16k_mono(audio)
        segments, info = model.transcribe(samples, beam_size=1, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
    except Exception as exc:  # noqa: BLE001 — a failed transcription is a reported state
        raise HTTPException(status_code=422, detail=f"Could not transcribe: {exc}") from exc
    return {"text": text, "language": getattr(info, "language", None),
            "duration_seconds": round(float(getattr(info, "duration", 0.0)), 2)}


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_SPEAK_CHARS)
    voice: Optional[str] = Field(default=None, max_length=40)
    speed: float = Field(default=1.0, ge=0.5, le=1.6)


@router.get("/voices")
def list_voices() -> Dict[str, Any]:
    """The installed English voices and the current one (read from the voices file itself)."""
    return voice_setting.state()


class VoiceChoice(BaseModel):
    voice: str = Field(..., max_length=40)
    changed_by: str = Field(default="operator", max_length=120)


@router.post("/voice")
def choose_voice(req: VoiceChoice) -> Dict[str, Any]:
    """Change OMEGA's speaking voice from a console (recorded). OMEGA can do the same with its
    set_voice command."""
    try:
        return voice_setting.set_voice(req.voice, changed_by=f"operator:{req.changed_by}",
                                       channel="desktop")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/speak")
def speak(req: SpeakRequest) -> Response:
    engine = _get_kokoro()
    voice = req.voice or voice_setting.current_voice()
    # Kokoro's first letter is the accent: a = American (en-us), b = British (en-gb). Every voice
    # used to be pronounced en-gb, so the American voices spoke with British phonemes.
    lang = "en-us" if voice.startswith("a") else "en-gb"
    try:
        samples, sample_rate = engine.create(req.text, voice=voice, speed=req.speed, lang=lang)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Could not speak: {exc}") from exc
    import soundfile as sf
    buffer = io.BytesIO()
    sf.write(buffer, samples, sample_rate, format="WAV")
    return Response(content=buffer.getvalue(), media_type="audio/wav")
