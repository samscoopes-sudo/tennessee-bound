"""Step 1 - transcription with word-level timestamps (faster-whisper, local).

Free and runs on CPU. Word timings are what let the director place stat
callouts on the exact spoken keyword.
"""
from __future__ import annotations

from functools import lru_cache

from .. import config
from .models import Transcript, TranscriptSegment, Word


@lru_cache(maxsize=1)
def _model():
    # Imported lazily so the app boots even if the model isn't downloaded yet.
    from faster_whisper import WhisperModel

    return WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")


def transcribe(video_path: str) -> Transcript:
    segments_iter, info = _model().transcribe(
        video_path, word_timestamps=True, vad_filter=True
    )

    segments: list[TranscriptSegment] = []
    for seg in segments_iter:
        words = [
            Word(text=w.word.strip(), start=w.start, end=w.end)
            for w in (seg.words or [])
            if w.start is not None and w.end is not None
        ]
        segments.append(
            TranscriptSegment(
                text=seg.text.strip(), start=seg.start, end=seg.end, words=words
            )
        )

    return Transcript(
        language=info.language,
        duration=info.duration,
        segments=segments,
    )
