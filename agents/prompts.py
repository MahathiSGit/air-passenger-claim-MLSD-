"""Versioned prompt artifacts loaded by the agent runtime."""
from __future__ import annotations
import json
from pathlib import Path
PROMPT_DIR = Path(__file__).with_name("prompts")
DEFAULT_VERSION = "v1"
def load_prompt(name: str, version: str = DEFAULT_VERSION) -> str:
    path = PROMPT_DIR / version / f"{name}.txt"
    return path.read_text(encoding="utf-8")
def list_versions(name: str) -> list[str]:
    return sorted(p.parent.name for p in PROMPT_DIR.glob(f"*/{name}.txt"))
