from __future__ import annotations

from pathlib import Path


FORBIDDEN_REFERENCES = ["execute_" + "message"]


def verify_ai_orchestration_integrity() -> dict:
    repo_root = Path(__file__).resolve().parents[1]
    detected: list[str] = []

    for path in repo_root.rglob("*.py"):
        if path.name == "ai_orchestration_integrity_check.py":
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for forbidden in FORBIDDEN_REFERENCES:
            if forbidden in content:
                detected.append(f"{path.relative_to(repo_root)}:{forbidden}")

    return {
        "success": len(detected) == 0,
        "legacy_execution_paths_detected": detected,
    }
