"""Shared config: the locked Appalachian look, pacing rules, and defaults."""
import os as _os

# --- Look (from broll-style.md). Appended in code so every b-roll shot matches. ---
# Qwen-Lightning runs at cfg~1, so the negative barely fires — the "make it rough,
# authentic, amateur" cues must live in the POSITIVE suffix, not the negative.
STYLE_SUFFIX = (
    "natural daylight, deep focus with everything sharp and fully in focus, "
    "no background blur, no bokeh, no depth-of-field blur, "
    "muted desaturated earthy colors, documentary photograph, "
    "photorealistic, sharp details, high clarity, "
    "not staged, not glossy, not cinematic, no warm grade, no text, no watermark"
)
NEGATIVE = (
    "cinematic, film still, dramatic lighting, golden hour, sunset, rim light, "
    "shallow depth of field, bokeh, blurred background, warm color grade, moody, artistic, "
    "beautiful, polished, professional photography, AI art, 3d render, oversaturated, HDR, "
    "staged, posed, deformed hands, extra fingers, text, watermark"
)

# --- Pacing (measured from the reference video: ~1 cut every 3s, median scene ~2.9s) ---
AVG_WORDS_PER_SEC = 2.5        # ~150 wpm narration; used to estimate shot timings
SHOT_SECONDS = 3.5            # ~3.5s/shot to match the reference creator's brisk cut cadence
TALKING_HEAD_MAX_SEC = 8.0    # never hold the avatar longer (InfiniteTalk sync + pacing)

# --- Content strategy: match Ezra Cade — ~75% Ken Burns STILLS + ~25% Wan MOTION, and
# motion only on shots whose subject naturally moves (steam, fire, boiling, pouring).
# False = the planner (and _reflag_motion) decides per shot; True = force every shot to Wan. ---
ALL_BROLL_MOTION = False

# --- Render dimensions (16:9) ---
STILL_W, STILL_H = 1920, 1080        # higher res stills for sharper output
VIDEO_W, VIDEO_H = 832, 480          # higher res avatar for sharper face detail
FPS = 25
WAN_FPS = 16                         # Wan 2.1 I2V native rate (VHS combine encodes at 16)

# --- FLUX.1-dev + Boreal amateur-photo LoRA (self-hosted stills on the pod, FREE) ---
# Boreal shifts FLUX to mundane cell-phone snapshots; trigger word is "photo", it's
# overtrained so strength stays < 1.0, and low guidance keeps it flat (not cinematic).
FLUX_LORA = 0.7
FLUX_LORA_PEOPLE = 0.35                 # lower LoRA for people — Boreal degrades faces at full strength
FLUX_GUIDANCE = 3.5
FLUX_STEPS = 20
FLUX_STEPS_PEOPLE = 25                  # more steps for people — better face/body detail
# Per-channel visual look (default = Appalachia). A channel overrides this via
# channel.json "style_suffix"; FLUX_ANTIHANDS is appended to EVERY channel.
FLUX_STYLE = ("candid documentary snapshot, soft natural light, muted earthy colors, "
              "mostly in focus, mundane and plain, photorealistic, "
              "not cinematic, not glossy, no text, no words, no letters, no signage, no watermark")

# When the shot has no people, steer FLUX away from generating hands/figures.
FLUX_ANTIHANDS = ("an unattended still life of objects alone, empty room, nobody present, "
                  "no people and no hands anywhere in the frame")
# When the shot DOES involve people, allow them but avoid close-up hand detail.
FLUX_PEOPLE = ("wide or medium shot showing full body or upper body, "
               "faces small in the frame, no extreme close-ups of faces, "
               "no detailed hands in foreground, natural proportions")

_PEOPLE_KEYWORDS = {"person", "people", "man", "woman", "men", "women", "crowd",
                    "group", "figure", "settler", "soldier", "farmer", "plumber",
                    "worker", "founder", "leader", "children", "family", "audience"}


def flux_prompt(subject: str, style: str | None = None) -> tuple[str, float, int]:
    """Boreal wants the trigger 'photo'; returns (prompt, lora_strength, steps).
    People shots get lower LoRA + more steps for better face quality."""
    subject = subject.strip().rstrip(",. ")
    words = set(subject.lower().split())
    has_people = bool(words & _PEOPLE_KEYWORDS)
    framing = FLUX_PEOPLE if has_people else FLUX_ANTIHANDS
    lora = FLUX_LORA_PEOPLE if has_people else FLUX_LORA
    steps = FLUX_STEPS_PEOPLE if has_people else FLUX_STEPS
    return f"photo of {subject}, {style or FLUX_STYLE}, {framing}", lora, steps

# --- Wan 2.2 5B (self-hosted on the pod, FREE) — the b-roll motion engine ---
WAN22_W, WAN22_H = 1280, 720         # higher res 16:9 for sharper stills/motion
WAN22_FPS = 14                       # low fps = slow, calm motion (like the competitor)
# NOTE: never put the word "camera" (or "hand", "person") here — Wan 2.2 renders it as a
# literal object in the frame. Describe the MOVE, not the equipment.
# Tiny, simple moves only (~a few centimeters). Rotated per motion shot for variety.
# Never put the word "camera"/"hand"/"person" here — Wan renders it as an object.
# PUSH-IN ONLY. Pans revealed new edge area that Wan filled with hallucinated
# hands/objects (see br_0017 grille, br_0026 hand-with-pan). A push-in crops inward,
# revealing nothing new. Also: NEVER name "hand"/"person"/"object"/"camera" here, even
# negated — at cfg~1 Wan draws the noun regardless. Describe ONLY the slow zoom + a frozen
# scene; the input still already fixes the content.
WAN22_MOTION_CUES = [
    "an extremely slow, gentle push-in toward the center, only a couple of centimeters. The scene stays completely frozen and unchanged, like a still photograph that barely zooms in. Calm, minimal, static.",
    "a barely perceptible slow zoom-in toward the middle of the frame. Everything is held perfectly still, a static photograph with the faintest push-in. Calm and unchanging.",
    "a very slow, smooth drift to the right revealing more of the scene. Everything stays still and grounded, like a slow-moving documentary shot. Calm and steady.",
    "a subtle slow pull-back revealing the full scene from close up. Gradual and unhurried, everything remains perfectly still. Quiet and atmospheric.",
]


def wan22_frames(duration: float) -> int:
    """Wan needs (4n+1) frames; length/fps = clip seconds. Round UP so it covers the shot."""
    import math
    n = max(1, math.ceil((duration * WAN22_FPS - 1) / 4))
    return 4 * n + 1

# Slow cinematic CAMERA movement — used only by the LOCAL Wan fallback (weak motion).
WAN_MOTION_CUE = ("slow cinematic camera push-in, smooth steady dolly movement, "
                  "gentle parallax, subtle atmospheric motion, no sudden movement")

# --- Cloud motion (fal.ai) — real subject motion. Primary path when FAL_KEY is set;
# falls back to local Wan otherwise. Seedance is ~5x cheaper than Hailuo. ---
# Switch models for A/B testing with:  export FAL_MOTION_MODEL=fal-ai/minimax/hailuo-02/standard/image-to-video
FAL_MOTION_MODEL = _os.environ.get("FAL_MOTION_MODEL",
                                   "fal-ai/bytedance/seedance/v1/lite/image-to-video")
if "hailuo" in FAL_MOTION_MODEL:                       # MiniMax Hailuo — better motion, ~$0.27
    FAL_MOTION_ARGS = {"duration": "6", "prompt_optimizer": True}
elif "seedance" in FAL_MOTION_MODEL:                   # ByteDance Seedance — cheap, ~$0.10
    FAL_MOTION_ARGS = {"resolution": "720p", "duration": "5"}
else:
    FAL_MOTION_ARGS = {"duration": "5"}

# Cloud STILL model (fal FLUX) — far more realistic than Qwen, and needs no pod.
# Used for b-roll stills + the source frame for Seedance when FAL_KEY is set.
# Switch with:  export FAL_STILL_MODEL=fal-ai/nano-banana   (Gemini "Nano Banana" — flat real look)
FAL_STILL_MODEL = _os.environ.get("FAL_STILL_MODEL", "fal-ai/nano-banana")
if "nano-banana" in FAL_STILL_MODEL or "gemini" in FAL_STILL_MODEL:
    FAL_STILL_ARGS = {"num_images": 1, "aspect_ratio": "16:9"}
else:                                                  # FLUX
    FAL_STILL_ARGS = {"image_size": "landscape_16_9", "num_inference_steps": 28,
                      "enable_safety_checker": False}
FAL_MOTION_CUE = ("very slow gentle camera push-in, subtle slow camera drift, "
                  "the subject stays almost still, minimal subject motion, "
                  "calm steady realistic, no fast movement, no distortion, no warping, "
                  "handheld documentary footage")


def wan_frames(duration: float) -> int:
    """Wan needs (4n+1) frames; round UP so the clip is never shorter than the shot."""
    import math
    n = max(1, math.ceil((duration * WAN_FPS - 1) / 4))
    return 4 * n + 1

# --- Talking head (InfiniteTalk) ---
# The avatar image + audio drive the clip; this prompt only guides subtle motion/mood.
TALKING_HEAD_PROMPT = (
    "a white middle-aged American man with glasses and short brown hair and gray goatee, "
    "wearing a dark navy button-down shirt, sitting at a desk with a laptop, "
    "speaking calmly to the camera, natural head movement, warm home office background, "
    "soft natural window lighting, documentary interview"
)
TALKING_HEAD_NEGATIVE = (
    "bright tones, overexposed, static, blurred details, subtitles, style, works, "
    "paintings, images, static, overall gray, worst quality, low quality, "
    "JPEG compression residue, ugly, incomplete, extra fingers, poorly drawn hands, "
    "poorly drawn faces, deformed, disfigured, misshapen limbs, fused fingers, "
    "still picture, messy background, three legs, many people in the background, walking backwards"
)

# --- Planner model ---
# Breaking paragraphs into shots is a simple structured task — Haiku does it fine at
# ~1/25th the cost of Opus. Bump to sonnet/opus only if shot choices feel weak.
#   export PLANNER_MODEL=claude-sonnet-4-6   (or claude-opus-4-8)
PLANNER_MODEL = _os.environ.get("PLANNER_MODEL", "claude-haiku-4-5")

# Scriptwriter: the full narration is worth the strongest model (planner stays cheap).
#   export SCRIPT_MODEL=claude-sonnet-5   to trade a little quality for cost
SCRIPT_MODEL = _os.environ.get("SCRIPT_MODEL", "claude-opus-4-8")


def styled(prompt: str) -> str:
    """Attach the locked style suffix to a bare subject prompt."""
    prompt = prompt.strip().rstrip(",. ")
    return f"{prompt}, {STYLE_SUFFIX}"
