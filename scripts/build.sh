#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root_dir="$(cd "$script_dir/.." && pwd)"

if [[ "$(uname -s)" == "Linux" ]] && ! command -v patchelf >/dev/null 2>&1; then
  printf '%s\n' "Missing required tool: patchelf"
  printf '%s\n' "Install with: sudo apt install -y patchelf"
  exit 1
fi

cd "$root_dir"
python3 scripts/build_nuitka.py

echo "Build complete."
