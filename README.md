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

## Install (source)

```bash
pip install -r requirements.txt
```

## Install (packaged)

Prebuilt packages are published in GitHub Releases:

- Release page: `https://github.com/TamKungZ/ImageMergePy/releases`

### Windows

- Microsoft Store: `https://apps.microsoft.com/detail/9ndnkpjpzt67`
- WinGet:

```powershell
winget install TamKungZ.ImageMerge
```

- Download and run `ImageMerge-windows-x64.msi`
- Or portable folder: extract `ImageMerge-windows-x64.zip`, then run `ImageMerge.exe`
- Microsoft Store submission asset is also generated as `ImageMergeGUI-windows-x64.msix`
- WinGet automation is configured for package id `TamKungZ.ImageMerge`

### Linux

- Debian/Ubuntu/Zorin: install `ImageMerge-linux-x64.deb`

```bash
sudo apt install ./ImageMerge-linux-x64.deb
```

- Fedora/RHEL/openSUSE: install `ImageMerge-linux-x64.rpm`

```bash
sudo rpm -Uvh ./ImageMerge-linux-x64.rpm
```

- AppImage: download `ImageMerge-linux-x64.AppImage`

```bash
chmod +x ImageMerge-linux-x64.AppImage
./ImageMerge-linux-x64.AppImage
```

- Flatpak bundle: `ImageMerge-linux-x64.flatpak`
- Snap artifact: `ImageMerge-linux-x64.snap` (store publishing workflow is configured)

### macOS

```bash
brew tap TamKungZ/tap
brew install --cask imagemerge
```

- App bundle zip: `ImageMerge-macos-app-arm64.zip` or `ImageMerge-macos-app-x64.zip`
- Binary zip: `ImageMerge-macos-binary-arm64.zip` or `ImageMerge-macos-binary-x64.zip`
- Homebrew cask publishing workflow is configured (`imagemerge`)

## Run (source)

```bash
python MainApp.py
```

## Run (CLI)

Use CLI mode without opening GUI:

```bash
python MainApp.py --cli --input "/path/to/folderA::full" --input "/path/to/folderB::short" --output "/path/to/output" --mode copy_keep
```

```bash
ImageMerge --cli --input "/path/a::full" --input "/path/b::short" --output "/path/out" --mode copy_keep
```

CLI options:

- `--input PATH[::PREFIX]` (repeatable)
- `--output PATH`
- `--mode copy_keep|copy_delete|move`
- `--clear-output`
- `--lang en|th`

In packaged builds, run the same options directly from the app binary (Windows/Linux/macOS).

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

Build step will auto-generate `embedded_locales.py` from `locales/*.json` before compiling.

Windows build also reads `app_metadata.json` and injects version/company/product metadata into the executable.

`build_nuitka.py` detects the current OS and builds native output:

- **Windows**: PE executable (`ImageMerge.exe`) under `dist/windows/ImageMerge.dist/`
- **Linux**: ELF binary (`ImageMerge`) under `dist/linux/ImageMerge.dist/`
- **macOS**:
  - Mach-O binary under `dist/macos-binary/ImageMerge.dist/`
  - `.app` bundle under `dist/macos-app/ImageMerge.app`

Note: cross-compiling to another OS is not configured; run the build on each target OS.

Architecture notes:

- Default CI runners currently publish x64 artifacts.
- The build scripts recognize these architecture labels: `x86`, `x64`, `arm`, `arm64`.
- To declare a target architecture in local/self-hosted builds, set `IMAGEMERGE_TARGET_ARCH` (cross-compilation toolchains are not auto-configured).

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

## Windows Metadata + Trust

Set app metadata in `app_metadata.json`:

- `company_name`, `product_name`, `file_description`
- `file_version`, `product_version`
- `icon_ico` (optional `.ico` path)

Optional signing is supported during build:

```powershell
$env:IMAGEMERGE_SIGN=1
$env:IMAGEMERGE_SIGN_PFX="C:\secure\codesign.pfx"
$env:IMAGEMERGE_SIGN_PASSWORD="<pfx-password>"
$env:IMAGEMERGE_SIGN_TIMESTAMP="http://timestamp.digicert.com"
./build.bat
```

For better SmartScreen reputation in production:

- Use a valid OV/EV code-signing certificate (EV is fastest for reputation).
- Keep publisher name consistent across releases.
- Sign both executable and installer.
- Avoid frequent publisher/certificate changes.

## Notes

- UI translations are embedded in code (no external locale files required at runtime).
- Source translation files are in `locales/en.json` and `locales/th.json`; embedded module is generated to `embedded_locales.py`.
- Kanit fonts are embedded in code and loaded at runtime (no external font files required at runtime).
- Set `IMAGEMERGE_LANG=en` or `IMAGEMERGE_LANG=th` to force language.

## Screenshots

<table>
  <tr>
    <td width="50%">
      <img src="https://dev.tamkungz.me/assets-image/imagemerge/imagemerge-start.png" alt="ImageMerge Start" width="100%" />
    </td>
    <td width="50%">
      <img src="https://dev.tamkungz.me/assets-image/imagemerge/imagemerge-mode.png" alt="ImageMerge Mode" width="100%" />
    </td>
  </tr>
  <tr>
    <td width="50%">
      <img src="https://dev.tamkungz.me/assets-image/imagemerge/imagemerge-options.png" alt="ImageMerge Options" width="100%" />
    </td>
    <td width="50%">
      <img src="https://dev.tamkungz.me/assets-image/imagemerge/imagemerge-add.png" alt="ImageMerge Add" width="100%" />
    </td>
  </tr>
</table>

<p align="center">
  <img src="https://dev.tamkungz.me/assets-image/imagemerge/imagemerge-icon.png" alt="ImageMerge Icon" width="20%" />
</p>

*By TamKungZ_*