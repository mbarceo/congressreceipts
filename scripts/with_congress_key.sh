#!/bin/zsh
# Runs one command with the congress.gov API key taken from the macOS Keychain (kept separate from the FEC key).
# Get a free key at https://api.congress.gov/sign-up/ and store it once (it prompts, so the key never appears on screen):
#   security add-generic-password -U -a "$USER" -s congress-api-key -w
# Usage:  ./scripts/with_congress_key.sh python3 -I scripts/fetch_bills.py
key=$(security find-generic-password -a "$USER" -s congress-api-key -w 2>/dev/null) || {
  echo "No congress.gov key in the Keychain. Store it with: security add-generic-password -U -a \"\$USER\" -s congress-api-key -w" >&2; exit 1; }
CONGRESS_API_KEY="$key" "$@"
