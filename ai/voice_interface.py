from __future__ import annotations


def transcribe_audio(payload: bytes) -> str:
    # Phase 7 hook: deterministic placeholder transcription
    if not payload:
        return ""
    return "voice_advisory_request"


def synthesize_audio(text: str) -> bytes:
    return text.encode("utf-8")
