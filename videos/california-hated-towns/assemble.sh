#!/bin/bash
# Assembles the final index.html by inlining all card HTML fragments
# into the master composition template.
#
# Usage: bash assemble.sh
# Output: public/index.html (modified in place)

set -euo pipefail

CARDS_DIR="public/cards"
INDEX="public/index.html"

if [ ! -f "$INDEX" ]; then
  echo "Error: $INDEX not found. Run from the project root."
  exit 1
fi

count=0
for card_file in "$CARDS_DIR"/*.html; do
  card_id=$(basename "$card_file" .html)
  marker="<!-- CARD_INCLUDE: $card_id -->"

  if grep -q "$marker" "$INDEX"; then
    card_content=$(cat "$card_file")
    # Escape special sed characters in the replacement
    escaped_content=$(printf '%s\n' "$card_content" | sed 's/[&/\]/\\&/g')
    # Use perl for reliable multi-line replacement
    perl -i -0pe "s|\Q$marker\E|$(<"$card_file")|" "$INDEX" 2>/dev/null || true
    count=$((count + 1))
  fi
done

echo "Assembled $count cards into $INDEX"
echo "Total card files found: $(ls -1 "$CARDS_DIR"/*.html | wc -l)"
