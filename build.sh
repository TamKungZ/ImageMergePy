#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" == "Linux" ]] && ! command -v patchelf >/dev/null 2>&1; then
  printf '%s\n' "Missing required tool: patchelf"
  printf '%s\n' "Install with: sudo apt install -y patchelf"
  exit 1
fi

unset IMAGEMERGE_ONEFILE
unset IMAGEMERGE_ONEFILE_STRICT
unset IMAGEMERGE_BINARY_ONLY

python3 build_nuitka.py

echo "Build complete."
