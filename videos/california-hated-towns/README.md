# The 10 Most HATED Towns in California — HyperFrames Overlay Project

Documentary-style text overlay composition using [HyperFrames](https://github.com/heygen-com/hyperframes).

## What This Does

Adds ~65 timed text overlays to your video:
- **10 lower-third town cards** (gold accent bar, town name, county, rank)
- **29 stat callouts** (data pills with gold highlights)
- **12 key phrase cards** (bold centered text with drop shadow)
- **10 region labels** (subtle upper-right location tags)
- **3 subscribe/CTA cards**

All overlays are composited on top of the B-roll using HyperFrames — the original video and audio are preserved untouched.

## Prerequisites

- **Node.js 22+**
- **FFmpeg / FFprobe** (system-installed)
- **Your video file** (the 2.5GB source MP4)

## Setup

```bash
# 1. Clone this repo and enter the project
cd videos/california-hated-towns

# 2. Install HyperFrames globally
npm install -g hyperframes

# 3. Check dependencies
npx hyperframes doctor

# 4. Copy fonts and GSAP from the HyperFrames skill assets
#    (If you installed skills: npx hyperframes skills update talking-head-recut)
#    The skill dir is typically at .claude/skills/talking-head-recut/assets/
#    Copy fonts/*.woff2 → public/fonts/
#    Copy vendor/gsap.min.js → public/vendor/

# 5. Prepare your video — re-encode with dense keyframes for seek accuracy
VIDEO_PATH="/path/to/your/video.mp4"
ffmpeg -y -i "$VIDEO_PATH" -c:v libx264 -crf 18 -g 30 -keyint_min 30 \
  -pix_fmt yuv420p -movflags +faststart -c:a aac "public/input-video.mp4"
```

## Render

```bash
# Preview in browser first
npx hyperframes preview public/index.html

# Lint check
npx hyperframes lint public/index.html

# Full render to MP4
npx hyperframes render public/index.html -o output.mp4
```

## Customization

- **Timing**: Edit `storyboard.json` and update the corresponding `data-start`/`data-duration` in `public/index.html`
- **Text content**: Edit individual card files in `public/cards/`
- **Colors**: The gold accent is `#FFB900`, theme uses noir palette (dark bg, light text)
- **Duration**: Update `data-duration` on the root `#stage` div and the video/audio elements to match your actual video length

## Project Structure

```
storyboard.json              — card timing plan (agent reference, not parsed by CLI)
public/
  index.html                 — master composition (video + all card overlays + GSAP timeline)
  input-video.mp4            — YOUR VIDEO (add after setup)
  cards/
    card-town-*.html         — 10 town lower-third cards
    card-stat-*.html         — 29 stat callout cards
    card-phrase-*.html       — 12 key phrase cards
    card-region-*.html       — 10 region label cards
    card-subscribe-*.html    — 3 CTA cards
  fonts/                     — Inter, Caveat woff2 files (from HyperFrames skill assets)
  vendor/
    gsap.min.js              — GSAP animation library (from HyperFrames skill assets)
```
