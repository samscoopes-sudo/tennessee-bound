#!/bin/bash
# Setup script for the California Hated Towns HyperFrames project
# Run this locally after cloning the repo.
#
# Usage: bash setup.sh /path/to/your/video.mp4

set -euo pipefail

VIDEO_PATH="${1:-}"

if [ -z "$VIDEO_PATH" ]; then
  echo "Usage: bash setup.sh /path/to/your/video.mp4"
  echo ""
  echo "This script will:"
  echo "  1. Install HyperFrames CLI"
  echo "  2. Install the talking-head-recut skill (provides fonts + GSAP)"
  echo "  3. Re-encode your video with dense keyframes for seek accuracy"
  echo "  4. Assemble all card overlays into the master composition"
  echo "  5. Run lint to validate the composition"
  exit 1
fi

if [ ! -f "$VIDEO_PATH" ]; then
  echo "Error: Video file not found: $VIDEO_PATH"
  exit 1
fi

echo "=== Step 1: Install HyperFrames ==="
npm install -g hyperframes 2>/dev/null || npx hyperframes --version

echo ""
echo "=== Step 2: Install skill assets (fonts + GSAP) ==="
npx hyperframes skills update talking-head-recut 2>/dev/null || true

# Find the skill directory
SKILL_DIR=""
for dir in .claude/skills/talking-head-recut node_modules/hyperframes/skills/talking-head-recut; do
  if [ -d "$dir/assets" ]; then
    SKILL_DIR="$dir"
    break
  fi
done

if [ -n "$SKILL_DIR" ]; then
  echo "Found skill assets at: $SKILL_DIR"
  cp -n "$SKILL_DIR/assets/fonts/"* public/fonts/ 2>/dev/null || true
  cp -n "$SKILL_DIR/assets/vendor/gsap.min.js" public/vendor/ 2>/dev/null || true
else
  echo "WARNING: Could not find skill assets directory."
  echo "You may need to manually copy:"
  echo "  - Inter font woff2 files to public/fonts/"
  echo "  - gsap.min.js to public/vendor/"
  echo ""
  echo "Alternatively, download from:"
  echo "  Fonts: https://fonts.google.com/specimen/Inter"
  echo "  GSAP: https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"
fi

echo ""
echo "=== Step 3: Re-encode video with dense keyframes ==="
echo "Input: $VIDEO_PATH"
echo "Output: public/input-video.mp4"
echo ""

# Get video duration for metadata
DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VIDEO_PATH" 2>/dev/null || echo "1160")
echo "Detected duration: ${DURATION}s"

ffmpeg -y -i "$VIDEO_PATH" \
  -c:v libx264 -crf 18 -g 30 -keyint_min 30 \
  -pix_fmt yuv420p -movflags +faststart \
  -c:a aac \
  public/input-video.mp4

echo ""
echo "=== Step 4: Assemble composition ==="
bash assemble.sh

echo ""
echo "=== Step 5: Validate ==="
npx hyperframes lint public/index.html 2>/dev/null || echo "(Lint check — review any warnings above)"

echo ""
echo "=== DONE ==="
echo ""
echo "Next steps:"
echo "  1. Preview:  npx hyperframes preview public/index.html"
echo "  2. Render:   npx hyperframes render public/index.html -o output.mp4"
echo ""
echo "NOTE: Update data-duration on #stage, #bg-video, and #source-audio"
echo "in public/index.html to match your actual video duration (${DURATION}s)"
echo "if it differs from 1160s (19:20)."
