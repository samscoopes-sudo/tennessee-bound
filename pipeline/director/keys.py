"""Shared API-key resolution: environment variable first, then a plain key file.

The local Bash tool here does not source shell profiles, so `export`ed keys can be
invisible; a `~/.<name>_key` file is the reliable fallback. Keys are never printed.
"""
from __future__ import annotations

import os
from pathlib import Path


def _from_file(*names: str) -> str | None:
    for n in names:
        p = Path(n).expanduser()
        if p.exists() and p.read_text().strip():
            return p.read_text().strip()
    return None


def anthropic_key() -> str:
    k = os.environ.get("ANTHROPIC_API_KEY") or _from_file("~/.anthropic_key")
    if not k:
        raise SystemExit("no Anthropic key found: set ANTHROPIC_API_KEY, or put it in ~/.anthropic_key")
    return k
