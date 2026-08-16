"""Shared data models for the edit pipeline.

The whole pipeline is organised around one artifact: the Edit Decision List
(EDL). The director LLM produces it; the compositor executes it. Keeping it a
typed, serialisable object is what lets the LLM "decide" while FFmpeg "renders"
deterministically.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Word(BaseModel):
    """A single transcribed word with its timing."""
    text: str
    start: float
    end: float


class TranscriptSegment(BaseModel):
    text: str
    start: float
    end: float
    words: list[Word] = Field(default_factory=list)


class Transcript(BaseModel):
    language: str
    duration: float
    segments: list[TranscriptSegment]

    def full_text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments).strip()


class CueType(str, Enum):
    BROLL = "broll"           # cover the avatar with footage/imagery
    LOWER_THIRD = "lower_third"  # name/title bar
    STAT = "stat"             # pop-in emphasis text on a keyword
    SPLIT_SCREEN = "split_screen"  # avatar on one third + reference imagery


class Motion(str, Enum):
    NONE = "none"
    KEN_BURNS_IN = "ken_burns_in"
    KEN_BURNS_OUT = "ken_burns_out"
    PAN = "pan"


class Cue(BaseModel):
    """One instruction on the timeline. `start`/`end` are seconds into the
    source avatar video. For instantaneous overlays (stat pop-ins) end may
    equal start and a default display length is applied at render time."""
    type: CueType
    start: float
    end: float

    # broll / split_screen
    query: Optional[str] = Field(
        default=None,
        description="Search/generation query describing the visual to source.",
    )
    prefer_source: Optional[
        Literal["storyblocks", "web_image", "cheap_image_gen", "ai_video_gen"]
    ] = None
    motion: Motion = Motion.KEN_BURNS_IN

    # text-bearing cues
    text: Optional[str] = None

    # populated by the asset stage once a file is sourced
    asset_path: Optional[str] = None
    asset_source: Optional[str] = None
    asset_is_video: bool = False


class EditDecisionList(BaseModel):
    """The director's full plan for one video."""
    style_preset: str = "default"
    energy: Literal["calm", "balanced", "punchy"] = "balanced"
    cues: list[Cue] = Field(default_factory=list)

    def broll_cues(self) -> list[Cue]:
        return [c for c in self.cues if c.type in (CueType.BROLL, CueType.SPLIT_SCREEN)]


class JobStatus(str, Enum):
    QUEUED = "queued"
    GENERATING_AVATAR = "generating_avatar"
    TRANSCRIBING = "transcribing"
    DIRECTING = "directing"
    SOURCING_ASSETS = "sourcing_assets"
    COMPOSING = "composing"
    DONE = "done"
    FAILED = "failed"


class Job(BaseModel):
    id: str
    status: JobStatus = JobStatus.QUEUED
    message: str = ""
    source_path: Optional[str] = None
    output_path: Optional[str] = None
    edl: Optional[EditDecisionList] = None
