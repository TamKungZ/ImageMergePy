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
python media_merge_gui.py
```

## Build EXE (PyInstaller)

Example one-file build command with bundled assets:

```bash
pyinstaller --noconfirm --onefile --windowed --name ImageMergePy --add-data "assets;assets" media_merge_gui.py
```

The built executable will be in the `dist/` folder.

## Notes

- Kanit fonts are stored in `assets/Kanit/` with license file `assets/Kanit/OFL.txt`.
- If Kanit is not available, the app falls back to `Segoe UI`.
