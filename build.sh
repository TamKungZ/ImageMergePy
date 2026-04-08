#!/usr/bin/env bash
set -euo pipefail

pyinstaller --noconfirm --clean --onefile --windowed --name ImageMerge --add-data "assets:assets" --add-data "locales:locales" MainApp.py

echo "Build complete: dist/ImageMerge"
