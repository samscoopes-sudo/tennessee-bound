"""Per-channel configuration.

Everything that DIFFERS between channels lives here (niche, narrator persona,
avatar image, voice, visual scene style, YouTube target). The shared *technical*
defaults — model files, render dims, FLUX/Wan/InfiniteTalk params — stay in
config.py and are the same for every channel.

Layout on disk:

    channels/
      <name>/
        channel.json      # the config below
        avatar.png        # this channel's narrator portrait (InfiniteTalk source)
        runs/
          <slug>/         # one video job
            shot-list.json
            output/       # br_*.png, th_*.mp4, br_*.mp4, video.mp4

A "run" is a single video (one topic on one day). `Channel.run_dir(slug)` makes
its working dir so channels never clobber each other.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

CHANNELS_DIR = Path(__file__).resolve().parent.parent / "channels"


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:60] or "untitled"


@dataclass
class Channel:
    name: str
    dir: Path
    title: str = ""
    # --- planning: what the channel is about + how the narrator is framed ---
    niche: str = ""               # e.g. "weathered rural Appalachian mountain/homestead"
    narrator_persona: str = ""    # e.g. "an older Appalachian man in voiceover; on camera only a few times"
    scene_style: str = ""         # b-roll still-life setting, e.g. "rustic Appalachian farmhouse kitchen"
    # --- assets / overrides ---
    avatar_file: str = "avatar.png"
    avatar_files: list[str] = field(default_factory=list)   # multiple angles; rotated across avatar shots
    avatar_count: int = 5              # how many on-camera avatar moments to inject
    style_suffix: str | None = None    # FLUX still-style override; None -> config.FLUX_STYLE
    script_notes: str = ""             # extra channel-specific scriptwriting guardrails
    planner_model: str | None = None   # None -> config.PLANNER_MODEL
    voice: dict = field(default_factory=dict)     # TTS settings (step 2)
    youtube: dict = field(default_factory=dict)   # upload target (step 5)
    raw: dict = field(default_factory=dict)

    # ---- resolved paths ----
    @property
    def avatar(self) -> Path:
        return self.dir / self.avatar_file

    @property
    def avatars(self) -> list[Path]:
        """All narrator angles (rotated across avatar shots); falls back to the single avatar."""
        return [self.dir / f for f in (self.avatar_files or [self.avatar_file])]

    @property
    def runs_dir(self) -> Path:
        d = self.dir / "runs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def run_dir(self, slug: str) -> Path:
        d = self.runs_dir / slugify(slug)
        (d / "output").mkdir(parents=True, exist_ok=True)
        return d

    def latest_run(self) -> Path | None:
        runs = [p for p in self.runs_dir.iterdir() if (p / "shot-list.json").exists()]
        return max(runs, key=lambda p: p.stat().st_mtime) if runs else None


def load(name: str) -> Channel:
    cdir = CHANNELS_DIR / name
    cfg = cdir / "channel.json"
    if not cfg.exists():
        avail = ", ".join(list_channels()) or "(none)"
        raise FileNotFoundError(f"No channel config at {cfg}. Available channels: {avail}")
    d = json.loads(cfg.read_text())
    ch = Channel(
        name=name,
        dir=cdir,
        title=d.get("title", name),
        niche=d.get("niche", ""),
        narrator_persona=d.get("narrator_persona", ""),
        scene_style=d.get("scene_style", ""),
        avatar_file=d.get("avatar", "avatar.png"),
        avatar_files=d.get("avatars", []),
        avatar_count=int(d.get("avatar_count", 5)),
        style_suffix=d.get("style_suffix"),
        script_notes=d.get("script_notes", ""),
        planner_model=d.get("planner_model"),
        voice=d.get("voice", {}),
        youtube=d.get("youtube", {}),
        raw=d,
    )
    if not ch.avatar.exists():
        raise FileNotFoundError(f"Channel '{name}' avatar missing: {ch.avatar}")
    return ch


def list_channels() -> list[str]:
    if not CHANNELS_DIR.exists():
        return []
    return sorted(p.name for p in CHANNELS_DIR.iterdir() if (p / "channel.json").exists())
