#!/bin/bash
# Helper script to verify card structure — the actual cards are in public/cards/
CARDS_DIR="videos/california-hated-towns/public/cards"
echo "Card count: $(ls -1 "$CARDS_DIR"/*.html 2>/dev/null | wc -l)"
