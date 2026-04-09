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
- New desktop UI built with `PySide6`
- Native builds with `Nuitka`

## Requirements

- Python 3.10+ (recommended)
- OS-specific native builds are supported on Windows, Linux, and macOS

## Install

```bash
pip install -r requirements.txt
```

## Run (source)

```bash
python MainApp.py
```

## Build (Nuitka)

Install dependencies first:

```bash
pip install -r requirements.txt
```

Then use the build scripts (or run `python build_nuitka.py` directly):

```bash
./build.sh
```

```bat
build.bat
```

`build_nuitka.py` detects the current OS and builds native output:

- **Windows**: PE executable (`ImageMerge.exe`) under `dist/windows/ImageMerge.dist/`
- **Linux**: ELF binary (`ImageMerge`) under `dist/linux/ImageMerge.dist/`
- **macOS**:
  - Mach-O binary under `dist/macos-binary/ImageMerge.dist/`
  - `.app` bundle under `dist/macos-app/ImageMerge.app`

Note: cross-compiling to another OS is not configured; run the build on each target OS.

Default build mode is `standalone` for reliability.

To force `onefile` mode (experimental on some Windows + Python/Nuitka versions):

```powershell
$env:IMAGEMERGE_ONEFILE=1
./build.bat
```

If onefile fails during payload step, update packaging deps and retry:

```powershell
python -m pip install -U "Nuitka[onefile]" zstandard
```

Also exclude your build folder from Windows Defender/antivirus scan during build.

## Notes

- UI translations are embedded in code (no external locale files required at runtime).
- Kanit fonts are embedded in code and loaded at runtime (no external font files required at runtime).
- Set `IMAGEMERGE_LANG=en` or `IMAGEMERGE_LANG=th` to force language.
