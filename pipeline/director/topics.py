"""Per-channel topic backlog with a dedup/produced log.

Ideation appends candidate topics (status "pending"); you approve a batch
("pending" -> "approved"); the daily run pops the next "approved" topic, writes it,
and marks it "produced" so it can never be picked again.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path


def _path(channel_dir: Path) -> Path:
    return Path(channel_dir) / "topics.json"


def load(channel_dir: Path) -> dict:
    p = _path(channel_dir)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"formula": "", "topics": []}


def save(data: dict, channel_dir: Path) -> None:
    _path(channel_dir).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _norm(title: str) -> str:
    # non-alphanumeric runs -> single space, so "Depression-Era" == "Depression Era"
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", title.lower())).strip()


def add_candidates(data: dict, cands: list[dict]) -> int:
    """Append new topics, skipping any whose title matches one already in the backlog
    (in any status). Returns how many were added."""
    seen = {_norm(t["title"]) for t in data["topics"]}
    added = 0
    for c in cands:
        n = _norm(c.get("title", ""))
        if not n or n in seen:
            continue
        seen.add(n)
        data["topics"].append({
            "title": c["title"].strip(),
            "pitch": c.get("pitch", "").strip(),
            "why": c.get("why", "").strip(),
            "status": "pending",
            "added": date.today().isoformat(),
        })
        added += 1
    return added


def approve_pending(data: dict) -> int:
    n = 0
    for t in data["topics"]:
        if t.get("status") == "pending":
            t["status"] = "approved"
            n += 1
    return n


def next_approved(data: dict) -> dict | None:
    for t in data["topics"]:
        if t.get("status") == "approved":
            return t
    return None


def set_status(data: dict, title: str, status: str) -> None:
    key = _norm(title)
    for t in data["topics"]:
        if _norm(t["title"]) == key:
            t["status"] = status
            if status == "produced":
                t["produced"] = date.today().isoformat()


def counts(data: dict) -> dict:
    out: dict[str, int] = {}
    for t in data["topics"]:
        out[t.get("status", "?")] = out.get(t.get("status", "?"), 0) + 1
    return out
