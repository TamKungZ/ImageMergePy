# ImageMerge

ImageMerge combines images and videos from folders, removes duplicate files,
and renames the results into an ordered sequence.

## Features

- Merge files from multiple folders, or organize files already in one folder.
- Copy, move, or copy and delete source files.
- Detect duplicates by file content and extension.
- Add an optional prefix to filenames.
- Stage changes in a temporary workspace by default; staged changes are applied
  only when processing completes.
- Sort media into predictable groups and rename them into one sequence.

## Sort priority

For a merge into an empty output folder, the rules below are applied from
highest to lowest priority. A lower rule is checked only when the files tie on
the rules above it. This means a `.png` always comes before a `.jpg`, even if
the JPG has a smaller filename number or is in an earlier input folder.

1. **Media type:** all images come before all videos.
2. **Extension:** files are grouped in this order:
   - Images: `.png` → `.jpg` → `.jpeg` → `.webp` → `.bmp` → `.gif` → `.tiff`
   - Videos: `.mp4` → `.mov` → `.mkv` → `.avi` → `.webm` → `.m4v` → `.wmv` → `.flv` → `.ts` → `.mts`
3. **Filename group, within the same extension:**
   1. `IMG` names with numbers, such as `IMG_2` and `IMG_10`
   2. UUID- or hash-style names
   3. Other names
4. **Order inside that filename group:**
   - `IMG` names: the number in the name, numerically (`IMG_2` before `IMG_10`)
   - UUID/hash names: file time, then name to break ties
   - Other names: leading number, numerically; then duplicate suffix such as
     `(1)`; then file time and name to break ties
5. **Output numbering:** after sorting, names are numbered continuously from
   `0001`; numbering does not restart for another extension or input folder.

The input folder's position and its prefix do **not** affect sort order. A
prefix is added to the resulting filename only.

Example input:

```text
trip/
├── 10.png
├── 2.png
└── 1.jpg
more/
├── 1.png
├── 3.jpg
└── 2.mp4
```

Result (with `trip` and `more` supplied as input prefixes):

```text
more-0001.png   # more/1.png
trip-0002.png   # trip/2.png
trip-0003.png   # trip/10.png
trip-0004.jpg   # trip/1.jpg
more-0005.jpg   # more/3.jpg
more-0006.mp4   # more/2.mp4
```

For organizer modes, the within-extension rule differs: existing sequence
numbers determine order in `main_folder`; in `inside_folder`, file modification
time determines order. Images still precede videos and extension priority still
comes before either rule.

## Download and install

Download the package for your operating system from
[GitHub Releases](https://github.com/TamKungZ/ImageMergePy/releases).

### Windows

- Install from the [Microsoft Store](https://apps.microsoft.com/detail/9ndnkpjpzt67)
  or with WinGet: `winget install TamKungZ.ImageMerge`.
- Or download and run `ImageMerge-windows-x64.msi`.
- The standalone ZIP does not install the app; extract it and run
  `ImageMerge.exe`.
- The MSI adds `ImageMerge` to `PATH`. Open a new terminal to use the CLI.

### Linux

- Ubuntu: install the `.deb` from Releases, or use the PPA on Ubuntu 22.04,
  24.04, or 26.04:

  ```bash
  sudo add-apt-repository ppa:tamkungz/stable
  sudo apt update
  sudo apt install imagemerge
  ```

- Fedora and compatible distributions: install the `.rpm`.
- AppImage, Flatpak, and Snap packages are also available in Releases.
- The `.deb`, `.rpm`, and PPA packages provide the `imagemerge` command.

### macOS

- Install with Homebrew:

  ```bash
  brew tap TamKungZ/tap
  brew install --cask imagemerge
  ```

- Or download the app bundle for Apple Silicon (`arm64`) or Intel (`x64`).
  Direct-download bundles are not signed or notarized, so Gatekeeper may block
  them.

## Command line

Packaged builds can run without opening the GUI. Repeat `--input` for each
source folder; a prefix can be added as `PATH::PREFIX`.

```bash
imagemerge --input "/path/to/photos::trip" --input "/path/to/videos" --output "/path/to/output" --mode copy_keep
```

On Windows, use `ImageMerge` instead of `imagemerge`.

Available modes:

- `copy_keep` (default): copy files and keep the originals.
- `copy_delete`: copy files, then delete the originals.
- `move`: move files to the output folder.
- `main_folder`: organize the output folder, then optionally import other
  folders. No `--input` is required.
- `inside_folder`: organize files in the output folder in place.

Input folders must already exist. `--clear-output` removes media files from the
output before processing. `--remove-duplicates` applies only to
`inside_folder`; `--allow-duplicates` imports matching files instead of
skipping them. Safe temporary staging is on by default; use `--no-safe-temp` to
write directly to the output folder.

## For developers

Run from source with Python 3.10 or later, install the dependencies in
`requirements.txt`, then launch with `python MainApp.py`. The native C ABI SDK
for calling ImageMerge from other languages is documented in
[`native/imagemerge-sdk`](native/imagemerge-sdk/README.md).

See [Releases.md](Releases.md) for version history.
