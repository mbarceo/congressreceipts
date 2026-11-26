#!/bin/zsh
# Runs one command with the FEC API key taken from the macOS Keychain, so the key is never stored in a file,
# the shell history or the project. Store it once (it prompts for the key, so it never appears on the command line):
#   security add-generic-password -U -a "$USER" -s fec-api-key -w
# Usage:  ./scripts/with_fec_key.sh python3 -I scripts/fetch_fec.py
# If FEC_API_KEY is already set (Linux, Windows/WSL, CI, or a one-off run), use it as is; otherwise read it from the macOS Keychain.
[[ -n "${FEC_API_KEY:-}" ]] && exec "$@"
key=$(security find-generic-password -a "$USER" -s fec-api-key -w 2>/dev/null) || {
  echo "No FEC key in the Keychain. Store it with: security add-generic-password -U -a \"\$USER\" -s fec-api-key -w" >&2; exit 1; }
FEC_API_KEY="$key" "$@"
