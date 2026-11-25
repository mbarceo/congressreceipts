#!/bin/zsh
# Runs the whole verification in order and refreshes the Sources page data.
# Rebuild the page data first if anything changed (see SCAFFOLD.md for that order).
cd "$(dirname "$0")/.." || exit 1
python3 -I scripts/extract_claims.py && \
python3 -I scripts/verify_bills.py && \
python3 -I scripts/verify_computed.py | tail -1 && \
python3 -I scripts/verify_all.py
