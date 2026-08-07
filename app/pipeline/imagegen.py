"""Cheap image-generation adapter (tier 3 of the asset ladder).

Wired for Gemini 2.5 Flash Image ("nano-banana") via the Google Generative
Language REST API - cheap, fast, good at on-brief 16:9 stills that stock won't
have. The still is then animated by the compositor's Ken Burns push-in, so a
generated image becomes "motion" for free.

Swap the endpoint/parsing if you use a different provider; the contract is
just: write an image to `dest`, return True on success.
"""
from __future__ import annotations

import base64
from pathlib import Path

import httpx

from .. import config

# Google Generative Language REST endpoint. IMAGE_GEN_MODEL defaults to
# "gemini-2.5-flash-image"; the key goes in as ?key=... per Google's API.
_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

# Nudge the model toward usable b-roll: real-looking, full-bleed, no text.
_STYLE_SUFFIX = (
    ", cinematic b-roll still, photorealistic, 16:9, natural lighting, "
    "no text, no watermark, no logos"
)


def generate_still(prompt: str, dest: Path) -> bool:
    if not config.IMAGE_GEN_API_KEY:
        return False

    url = _ENDPOINT.format(model=config.IMAGE_GEN_MODEL)
    body = {
        "contents": [
            {"parts": [{"text": f"Generate an image: {prompt}{_STYLE_SUFFIX}"}]}
        ],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    try:
        r = httpx.post(
            url,
            params={"key": config.IMAGE_GEN_API_KEY},
            json=body,
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()

        # Find the first inline image part in the response.
        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    dest.write_bytes(base64.b64decode(inline["data"]))
                    return dest.stat().st_size > 0
        return False
    except Exception:
        return False
