#!/bin/zsh
# Runs the whole verification in order and refreshes the Sources page data.
# Rebuild the page data first if anything changed (see SCAFFOLD.md for that order).
S="$(cd "$(dirname "$0")" && pwd)"; cd "${TRACKER_DIR:-$S/..}" || exit 1
python3 -I "$S"/extract_claims.py && \
python3 -I "$S"/verify_bills.py && \
python3 -I "$S"/verify_computed.py | tail -1 && \
python3 -I "$S"/verify_all.py
