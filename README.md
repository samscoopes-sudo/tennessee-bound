# Video Agent - b-roll & motion graphics

Upload a raw avatar (talking-head) video, get it back edited in the house
style: b-roll footage over the speaker, Ken Burns motion on stills, clean
lower-thirds, and stat pop-ins on spoken numbers. Cheap by design - real
footage comes from your Storyblocks subscription first, and AI generation is a
budget-capped last resort.

## How it works

```
raw avatar.mp4
  |
  |- 1. transcribe   faster-whisper (local, free) -> word-level timestamps
  |- 2. direct       Claude reads transcript + style preset -> Edit Decision List
  |- 3. source       fallback ladder: Storyblocks -> web stills -> image gen -> AI video
  |- 4. compose      FFmpeg executes the EDL (hard cuts, Ken Burns, drawtext)
       |
   edited.mp4
```

The **director LLM only decides** (what/when); **FFmpeg renders**
deterministically. That split keeps it cheap and reliable. The house style
lives in [`style-presets/default.json`](style-presets/default.json).

## No camera? Generate the avatar too (Duix.Avatar)

You can skip the recording step entirely and have the talking-head *generated*
from a script, then edited by the same pipeline. This uses
[Duix.Avatar](https://github.com/duixcom/Duix-Avatar) - a free, fully offline
digital-human toolkit (voice clone + lip-synced face synthesis) that runs as
local Docker services on an NVIDIA GPU.

```
script + face reference
  |- 0. avatar   Duix.Avatar: TTS (voice clone) -> face2face lip-sync
       |
  raw avatar.mp4  --> steps 1-4 above --> edited.mp4
```

Deploy Duix.Avatar's `docker-compose` (see its repo), then set
`DUIX_GEN_VIDEO_URL`, `DUIX_TTS_URL` and `DUIX_DATA_DIR` (see
[`.env.example`](.env.example)). `DUIX_DATA_DIR` must be the same shared volume
its containers mount, since files are exchanged through it. Then:

```bash
curl -F script="Hi, here's this week's update..." \
     -F face_video=@face.mp4 \
     -F voice_reference=@my_voice.wav \
     http://localhost:8000/api/avatar-jobs
```

Supply the speech as `voice_reference` (a short sample, cloned onto the script)
or as a ready-made `audio` narration file. Poll `GET /api/jobs/{id}` and
download as usual. `GET /health` reports `duix_avatar_enabled`. The client
lives in [`app/pipeline/avatar.py`](app/pipeline/avatar.py); when Duix isn't
configured the endpoint returns 503 and the rest of the app is unaffected.

## Cost model

| Step | Tool | Cost |
|---|---|---|
| Transcription | faster-whisper (local) | free |
| Director | Claude API | ~cents/video |
| B-roll footage | Storyblocks (subscribed) | free marginal |
| Web stills | Pexels | free |
| Custom stills | cheap image gen | ~$0.04 each |
| AI video | last resort, capped | avoided |

Typical 60s video ~ **$0.10-0.40**.

## Run locally

```bash
pip install -r requirements.txt          # needs ffmpeg on PATH
cp .env.example .env                      # fill in ANTHROPIC_API_KEY (min)
set -a; . ./.env; set +a
uvicorn app.main:app --reload
# open http://localhost:8000
```

Or with Docker (bundles ffmpeg + fonts):

```bash
docker build -t video-agent .
docker run -p 8000:8000 --env-file .env video-agent
```

## Deploy

`render.yaml` is a Render blueprint: push this repo, create a Blueprint from
it, then set the secret env vars (at minimum `ANTHROPIC_API_KEY`) in the
dashboard. Any Docker host (Railway, Fly.io, Cloud Run) works too - it's a
single container serving `/`.

Set only the asset keys you have; each missing key just skips that tier of the
ladder. `GET /health` reports which sources are active.

## Configuration

All via env vars - see [`.env.example`](.env.example). Key knobs: `energy`
(picked per-upload in the UI), `WHISPER_MODEL`, `MAX_AI_VIDEO_SECONDS` (cost
cap). Wire your image/video providers in `app/pipeline/imagegen.py` and
`app/pipeline/videogen.py`.

## Project layout

```
app/
  main.py              FastAPI: upload / status / download + UI
  config.py            env-driven config
  static/index.html    upload UI with live progress
  pipeline/
    models.py          EDL + job types
    avatar.py          Duix.Avatar client (optional script -> talking-head)
    transcribe.py      faster-whisper
    director.py        Claude -> EDL
    assets.py          fallback ladder
    imagegen.py        cheap image-gen adapter (Gemini)
    videogen.py        ai video adapter (last resort)
    compose.py         FFmpeg compositor
    run.py             orchestrates the 4 steps
style-presets/         house editing style (JSON the director reads)
```
