# ImageMergePy

A GUI tool to merge images/videos from multiple folders, remove duplicates with SHA-256, and rename files into a clean sequential format.

## Features

- Merge media from multiple input folders into one output folder
- De-duplicate files using `SHA-256 + file extension`
- Supports 3 operation modes
  - `copy_keep`: copy only, keep source files
  - `copy_delete`: copy, then delete source files
  - `move`: move files from input to output
- Set a per-folder `prefix`
- Rename files as `prefix-0001.jpg` or `0001.jpg`
- Keep output ordered: images first, videos last
- Supports building a `.exe` with PyInstaller

## Requirements

- Python 3.10+ (recommended)
- Windows (the UI uses `tkinter` and registers Kanit fonts on Windows)

## Install

```bash
pip install -r requirements.txt
```

## Run (source)

```bash
python MainApp.py
```

## Build EXE (PyInstaller)

Use build scripts:

```bash
./build.sh
```

```bat
build.bat
```

Or run PyInstaller directly:

```bash
pyinstaller --noconfirm --clean --onefile --windowed --name ImageMerge --add-data "assets;assets" --add-data "locales;locales" MainApp.py
```

The built executable will be in the `dist/` folder.

## Notes

- Kanit fonts are stored in `assets/Kanit/` with license file `assets/Kanit/OFL.txt`.
- If Kanit is not available, the app falls back to `Segoe UI`.
- Language files are in `locales/en.json` and `locales/th.json`.
- Set `IMAGEMERGE_LANG=en` or `IMAGEMERGE_LANG=th` to force language.
