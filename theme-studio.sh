#!/bin/sh
# Ghoul Cyber - Theme Studio (Linux launcher)
cd "$(dirname "$0")" || exit 1
exec python3 theme_studio.py "$@"
