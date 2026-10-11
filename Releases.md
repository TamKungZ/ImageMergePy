Tag: v2.0.2
Release title: v2.0.2 - Runtime Robustness Fixes + v2.0.1 Fixes
Release notes:
## ImageMerge v2.0.2

This release replaces v2.0.1, which was released with errors. It contains every fix from
v2.0.1 (Launchpad PPA package, Nuitka build paths, and the Windows start-up crash) and
adds fixes found while reviewing the code for real-world use: files imported twice in the
Main folder workflow, junk files imported as photos, wrong ordering on Linux, and several
ways a long run could fail badly or leave files behind.

### Highlights
#### New in v2.0.2
- Fixed Main folder importing the output folder's own files again
  - Choosing a source folder that contains the output folder (for example the parent folder) together with "allow duplicates" copied every existing file back into the output on each run
  - The output folder is now skipped when scanning sources
- Junk files are no longer imported as media
  - macOS `._name.jpg` sidecar files (common on external drives) are skipped
  - Thumbnail and trash folders are skipped: `@eaDir` (Synology), `.AppleDouble`, `.thumbnails`, `$RECYCLE.BIN`, `.Trash` and `.Trash-*`
- Fixed the order of files with UUID or hash names on Linux
  - `getctime` is the inode-change time on Linux, not the creation time; the app now uses the creation time on Windows and macOS and the modified time on Linux
- A full disk now stops the job at the first error instead of failing every remaining file one by one (in safe mode the staging folder is discarded and nothing is applied)
- Input and output paths are now validated for every workflow
  - A missing source folder gives a clear error instead of "found 0 files"
  - An output path that is a file is rejected
- Fixed the app failing at start-up when neither the `locales` folder nor `_embedded_locales.py` is present; it now falls back to English
- Safe workspace folders left behind by a crash or a killed process (`.imagemerge_temp/session-*`) are removed automatically once they are older than 24 hours
- Closing the window while a job is still copying a large file no longer destroys the running thread; the window stays open until the job has stopped
- `error.log` is rotated to `error.log.old` when it grows past 1 MB
- Fixed a start-up failure being hidden by a second error: a function-local `import traceback` in `entry.py` made `traceback` unbound in the GUI error path, so a failed GUI start ended with `UnboundLocalError` and nothing useful in `error.log`; the original error and its traceback are now written to `error.log`
- The Linux CI jobs now install the Qt runtime libraries (`libegl1`, `libgl1`, `libxkbcommon`, `libxcb-*`) before the GUI smoke test; the `.deb` already declared them as dependencies, but the hosted runner did not have `libEGL.so.1`
- Updated application version metadata to `2.0.2`

#### Carried over from v2.0.1
- Fixed the Windows app not opening at all (no window, no message) when installed from the MSI
  - The process crashed with exception `0xc0000409` right after Qt loaded `qmodernwindowsstyle.dll`; Nuitka reported a segmentation fault in the native `windows11` Qt style plugin (Qt 6.12)
  - The app now always uses the `Fusion` style (`QT_STYLE_OVERRIDE` is set before the `QApplication` is created, and `setStyle("Fusion")` is called after), which avoids that plugin and matches the app's own stylesheet and palette
  - Setting `QT_STYLE_OVERRIDE=Fusion` on an affected 2.0.1 install makes it start, for anyone who has already installed it
- The GUI now writes startup problems to `%LOCALAPPDATA%\ImageMerge\error.log` (Qt messages including fatal ones, Python tracebacks, and native crash traces) and shows an error dialog on Windows if startup fails with a Python exception, instead of closing silently
- Fixed `exec: /opt/ImageMerge/ImageMerge: Permission denied` after installing from the PPA
  - `extract_runtime()` used `zipfile.extractall()`, which does not restore Unix file permissions, so the `ImageMerge` executable was packaged as `0644`
  - The runtime is now extracted file by file with permissions restored from the zip, and `ImageMerge` is always forced to `0755`
  - Symlinks in the runtime archive are now handled safely, and unsafe paths such as `../` are still rejected
  - The build now stops if any file from the zip is missing on disk after extraction
- Fixed `ImportError: /opt/ImageMerge/_opcode.so: cannot open shared object file`
  - `dpkg-source` applies a default ignore list that silently drops `*.so`, `*.a`, `*.la`, `*.o`, and `.git*` files from the source tarball; the runtime's Python extension modules and bundled Qt libraries are all `*.so`
  - Added `-I.imagemerge-keep-everything` to the `dpkg-buildpackage` call, which replaces the default ignore list with a pattern that matches nothing
- Added a source tarball integrity check: the build compares the number of regular runtime files in the build tree with the number inside the generated `.tar.xz` and refuses to upload if any file was dropped
- Packaging files under `debian/` and `packaging/` are now converted to LF line endings before building, so a Windows checkout with CRLF can no longer break `debian/rules` or the launcher script
- Added `override_dh_makeshlibs:` to `debian/rules` so `dh_makeshlibs` does not register the bundled runtime libraries as system shared libraries
- Fixed `app_metadata.json` not being found in compiled builds
  - `APP_DIR` in `metadata.py` assumed the source layout (`parents[2]`), but in a standalone build the module lives in `<dist>/media_merge/`, so the path pointed outside the dist folder and the About page showed version `-`
  - Compiled builds now detect `__compiled__` and resolve the dist folder from the module name, so it works whether the package is imported as `media_merge` or `src.media_merge`
- Fixed bundled fonts not loading when the app is started through `PATH` on Linux: `fonts.py` used `sys.argv[0]`, which can be a bare file name; it now uses `APP_DIR / "fonts"`
- The Windows signing step in `build_nuitka.py` no longer prints the certificate password in the logged `signtool` command (shown as `***`), and the password is no longer stripped. Signing only runs when `IMAGEMERGE_SIGN=1`, which the release workflows do not set
- Build cleanup now removes the generated `_embedded_locales.py` as well as the old `_embedded_fonts.py`, and a duplicated font-folder cleanup was removed
- Architecture detection in `build_nuitka.py` now reads the running Python interpreter, so a 32-bit Python on 64-bit Windows is no longer reported as x64; the log line now says "Resolved target architecture"

### Verification
#### v2.0.2
- `python3 -m py_compile` passes for every module in `src/media_merge`
- `tests/test_stable_ordering.py`, `tests/test_build_nuitka.py` and `tests/test_launchpad_package.py` pass
- An end-to-end script ran Copy keep, Copy delete and Move, each with and without the safe workspace, and checked the added, skipped and failed counts, gapless numbering, that sources are removed or kept as expected, and that no staging folder is left
- The same script checked dry run, cancel, simulated disk full, a simulated single-file error, stale-session cleanup, tidy with duplicate removal, input and output validation, and the CLI (`--lang th`, prefix, missing input exits with code 2)
- Still to check on a real build: the GUI close-while-running behaviour (PySide6 was not available in the test environment)

#### v2.0.1
- `python3 -m py_compile scripts/build_launchpad_source.py` passes
- Reproduced the `Permission denied` cause: the zip stores `0755` but `extractall()` produced `0644`; the new extraction keeps `0755`, and a zip without the executable bit still ends up `0755`
- Reproduced the missing-file cause: without `-I`, `_opcode.so`, `_ctypes.so`, `PySide6/QtCore.so`, and `libfoo.a` were left out of the tarball; with `-I.imagemerge-keep-everything` they were all kept
- Confirmed that `../` paths in the runtime archive are rejected
- Checked the build-script and path changes by reading the code against the build and release workflows, and simulated the source and compiled path resolution
- Reproduced the Windows crash on a Windows 11 install of the MSI: exit code `-1073740791` (`0xc0000409`), with the app starting normally when `QT_STYLE_OVERRIDE=Fusion` is set and still crashing with `QT_QPA_PLATFORM=windows:fontengine=freetype`, which points at the `windows11` style rather than font loading
- Confirmed from source that the GUI starts offscreen with the `fusion` style active and that `error.log` is created
- Still to check in a real Windows build: the installed app opens without setting any environment variable
- Still to check in real builds on all three platforms: About page shows the correct version, window icon appears, and Thai and Japanese fonts load from the `fonts` folder
- Full `dpkg-buildpackage` and running `imagemerge` after install will be exercised by the publish workflow on the new tag

### Known issues (not changed in this release)
- `tests/test_cli.py` and `tests/test_media_operations.py` still use the old dict-based API and fail (5 tests); they failed before this release too
- `src/media_merge/media_ops.py` is legacy code that only those old tests use
- `.ts` is treated as a video extension, so TypeScript files in a source folder are imported as videos
- Committing the safe workspace is not atomic, and there is no lock against two instances using the same output folder
- Move mode with the safe workspace needs free space equal to the size of the files being moved

### Upgrade
Everyone on v2.0.1 should upgrade to v2.0.2. No settings or data changes are needed; download the new build from the Releases page and replace the previous version.

Users on `2.0.0ubuntu22.04.1` from the PPA need to upgrade; the missing files cannot be repaired on the client. Running `chmod +x` only fixes the permission error, not the missing `_opcode.so`.

```bash
sudo apt update
sudo apt install --only-upgrade imagemerge
ls -la /opt/ImageMerge/ImageMerge /opt/ImageMerge/_opcode.so
imagemerge --cli --input /path/to/folder --output /path/to/output
```

### Note
The Windows start-up crash only affected the GUI; `ImageMerge --cli` worked, so the WinGet smoke test (which runs the CLI) did not catch it.

The CLI flag is `--cli` with two dashes, and it requires `--input` and `--output`. The single-dash form `-cli` is not recognized by the argument parser and is unrelated to these two errors.

The Permission denied and `_opcode.so` errors only affected the Launchpad PPA package; the GitHub Release `.deb` built with fpm was not affected.

### License
This project remains open-source under the **MIT License**.

---

Tag: v2.0.1
Release title: v2.0.1 - Launchpad Package + Build Fixes
Release notes:
## ImageMerge v2.0.1

> **Note:** v2.0.1 was released with errors. Please use v2.0.2 instead; it includes every fix listed below and further fixes.

Maintenance release that fixes two bugs in the Launchpad PPA package
(`2.0.0ubuntu22.04.1`) that made `imagemerge` fail to start on Ubuntu and WSL,
and fixes file-path and build-script problems in compiled (Nuitka) builds on
all platforms. It also fixes the Windows app closing immediately without any
message when it is opened from the MSI install.

### Highlights
- Fixed the Windows app not opening at all (no window, no message) when installed from the MSI
  - The process crashed with exception `0xc0000409` right after Qt loaded `qmodernwindowsstyle.dll`; Nuitka reported a segmentation fault in the native `windows11` Qt style plugin (Qt 6.12)
  - The app now always uses the `Fusion` style (`QT_STYLE_OVERRIDE` is set before the `QApplication` is created, and `setStyle("Fusion")` is called after), which avoids that plugin and matches the app's own stylesheet and palette
  - Setting `QT_STYLE_OVERRIDE=Fusion` on an affected 2.0.1 install makes it start, for anyone who has already installed it
- The GUI now writes startup problems to `%LOCALAPPDATA%\ImageMerge\error.log` (Qt messages including fatal ones, Python tracebacks, and native crash traces) and shows an error dialog on Windows if startup fails with a Python exception, instead of closing silently
- Fixed `exec: /opt/ImageMerge/ImageMerge: Permission denied` after installing from the PPA
  - `extract_runtime()` used `zipfile.extractall()`, which does not restore Unix file permissions, so the `ImageMerge` executable was packaged as `0644`
  - The runtime is now extracted file by file with permissions restored from the zip, and `ImageMerge` is always forced to `0755`
  - Symlinks in the runtime archive are now handled safely, and unsafe paths such as `../` are still rejected
  - The build now stops if any file from the zip is missing on disk after extraction
- Fixed `ImportError: /opt/ImageMerge/_opcode.so: cannot open shared object file`
  - `dpkg-source` applies a default ignore list that silently drops `*.so`, `*.a`, `*.la`, `*.o`, and `.git*` files from the source tarball; the runtime's Python extension modules and bundled Qt libraries are all `*.so`
  - Added `-I.imagemerge-keep-everything` to the `dpkg-buildpackage` call, which replaces the default ignore list with a pattern that matches nothing
- Added a source tarball integrity check: the build compares the number of regular runtime files in the build tree with the number inside the generated `.tar.xz` and refuses to upload if any file was dropped
- Packaging files under `debian/` and `packaging/` are now converted to LF line endings before building, so a Windows checkout with CRLF can no longer break `debian/rules` or the launcher script
- Added `override_dh_makeshlibs:` to `debian/rules` so `dh_makeshlibs` does not register the bundled runtime libraries as system shared libraries
- Fixed `app_metadata.json` not being found in compiled builds
  - `APP_DIR` in `metadata.py` assumed the source layout (`parents[2]`), but in a standalone build the module lives in `<dist>/media_merge/`, so the path pointed outside the dist folder and the About page showed version `-`
  - Compiled builds now detect `__compiled__` and resolve the dist folder from the module name, so it works whether the package is imported as `media_merge` or `src.media_merge`
- Fixed bundled fonts not loading when the app is started through `PATH` on Linux: `fonts.py` used `sys.argv[0]`, which can be a bare file name; it now uses `APP_DIR / "fonts"`
- The Windows signing step in `build_nuitka.py` no longer prints the certificate password in the logged `signtool` command (shown as `***`), and the password is no longer stripped. Signing only runs when `IMAGEMERGE_SIGN=1`, which the release workflows do not set
- Build cleanup now removes the generated `_embedded_locales.py` as well as the old `_embedded_fonts.py`, and a duplicated font-folder cleanup was removed
- Architecture detection in `build_nuitka.py` now reads the running Python interpreter, so a 32-bit Python on 64-bit Windows is no longer reported as x64; the log line now says "Resolved target architecture"
- Updated application version metadata to `2.0.1`

### Verification
- `python3 -m py_compile scripts/build_launchpad_source.py` passes
- Reproduced the `Permission denied` cause: the zip stores `0755` but `extractall()` produced `0644`; the new extraction keeps `0755`, and a zip without the executable bit still ends up `0755`
- Reproduced the missing-file cause: without `-I`, `_opcode.so`, `_ctypes.so`, `PySide6/QtCore.so`, and `libfoo.a` were left out of the tarball; with `-I.imagemerge-keep-everything` they were all kept
- Confirmed that `../` paths in the runtime archive are rejected
- Checked the build-script and path changes by reading the code against the build and release workflows, and simulated the source and compiled path resolution
- Reproduced the Windows crash on a Windows 11 install of the MSI: exit code `-1073740791` (`0xc0000409`), with the app starting normally when `QT_STYLE_OVERRIDE=Fusion` is set and still crashing with `QT_QPA_PLATFORM=windows:fontengine=freetype`, which points at the `windows11` style rather than font loading
- Confirmed from source that the GUI starts offscreen with the `fusion` style active and that `error.log` is created
- Still to check in a real Windows build: the installed app opens without setting any environment variable
- Still to check in real builds on all three platforms: About page shows the correct version, window icon appears, and Thai and Japanese fonts load from the `fonts` folder
- Full `dpkg-buildpackage` and running `imagemerge` after install will be exercised by the publish workflow on the new tag

### Upgrade
Users on `2.0.0ubuntu22.04.1` from the PPA need to upgrade; the missing files cannot be repaired on the client. Running `chmod +x` only fixes the permission error, not the missing `_opcode.so`.

```bash
sudo apt update
sudo apt install --only-upgrade imagemerge
ls -la /opt/ImageMerge/ImageMerge /opt/ImageMerge/_opcode.so
imagemerge --cli --input /path/to/folder --output /path/to/output
```

### Note
The Windows start-up crash only affected the GUI; `ImageMerge --cli` worked, so the WinGet smoke test (which runs the CLI) did not catch it.

The CLI flag is `--cli` with two dashes, and it requires `--input` and `--output`. The single-dash form `-cli` is not recognized by the argument parser and is unrelated to these two errors.

The Permission denied and `_opcode.so` errors only affected the Launchpad PPA package; the GitHub Release `.deb` built with fpm was not affected.

### License
This project remains open-source under the **MIT License**.

---

Tag: v2.0.0
Release title: v2.0.0 - Project Reorganization + Build Refresh
Release notes:
## ImageMerge v2.0.0

A major maintenance release focused on a cleaner project structure and more
reliable native builds.

### Highlights
- Reorganized application and build resources to make the project easier to maintain
- Split media processing into focused modules for shared models and constants, file operations, hashing, safe workspaces, merge processing, and in-place organization
- Refactored the Qt interface into focused page, source-list, run-panel, dialog, font, and theme modules
- Improved duplicate detection by checking file size and extension before hashing, then caching hashes for matching candidates
- Safe workspace staging now uses hard links when supported, with file-copy fallback
- Improved CLI validation for missing or invalid input folders and output paths nested inside input folders
- Added clearer cancellation behavior and status messages in English and Thai; safe mode discards staged changes when cancelled
- Load only the active and fallback translation catalogs, and discover available languages from locale files
- Refreshed application icons for Windows, Linux, and macOS using the updated artwork
- Build scripts download pinned Noto Sans fonts for Latin, Thai, Japanese,
  Korean, Simplified Chinese, and Arabic, verifying SHA-256 checksums instead
  of storing font binaries in the repository
- Removed the slow Windows one-file executable; Windows distribution uses an installer and a clean standalone folder package
- Cleaned build output to avoid leaving unnecessary caches and intermediate files
- Redesigned the interface with a navigation sidebar, numbered steps, and a bottom action bar showing status, results, progress, and a collapsible log
- Renamed workflows by what they do: Merge folders, Add to library, and Tidy a folder
- Added drag and drop of folders onto the folder lists, and an Open folder button after a run finishes
- Added a confirmation before any run that deletes files, and locked the inputs while a job is running
- Fixed Add to library offering Clear output folder first, which removed the existing library before sorting; it is no longer offered there and is now off by default in Merge folders
- Updated application version metadata to `2.0.0`

### Distribution
- Windows MSI installer, standalone ZIP, and Microsoft Store MSIX submission package
- Linux `.deb`, `.rpm`, AppImage, Flatpak, Snap, and standalone ZIP packages
- macOS x64 and arm64 app-bundle and standalone ZIP packages

### License
This project remains open-source under the **MIT License**.

---

Tag: v1.1.2
Release title: v1.1.2 - Optional Duplicate Import
Release notes:
## ImageMerge v1.1.2

Update focused on giving every workflow explicit control over duplicate handling.

### Highlights
- Added an **Allow duplicate files** checkbox to the Merge workflow options
- Added the same duplicate-import option to Main Folder and Inside Folder Organizer workflows
- When enabled, files with matching hash + extension are no longer skipped and are still sorted and renamed normally
- Main Folder workflow avoids copying existing output files back onto themselves while still allowing duplicate imports from selected folders
- Inside Folder Organizer now disables duplicate removal behavior when duplicate files are explicitly allowed
- Added CLI support with `--allow-duplicates`
- Added English and Thai localization strings for the new option
- Updated executable metadata version to `1.1.2.0`

### Verification
- `python -m compileall MainApp.py src`
- `git diff --check`

### License
This project remains open-source under the **MIT License**.

---

Tag: v1.1.1
Release title: v1.1.1 - Streamlined UI + 16:9 Window
Release notes:
## ImageMerge v1.1.1

Update focused on making every workflow easier to understand and operate.

### Highlights
- Redesigned the Merge page as a clear four-step workflow: input folders, output folder, operation mode, and options
- Grouped related controls into cleaner cards with improved spacing and visual hierarchy
- Refined workflow navigation so the active page is easier to identify
- Added a readiness summary beside the Start button
- Start is now enabled only when the required source and destination selections are complete
- Improved mode selection cards and kept processing statistics and logs visible in the right panel
- Refined the Main Folder and Inside Folder Organizer layouts for consistency
- Set the initial application window size to `1280x720` (16:9)
- Added English and Thai localization strings for the redesigned interface
- Updated executable metadata version to `1.1.1.0`

### Verification
- `python -m compileall src MainApp.py`
- Validated English and Thai locale JSON files
- Rendered all three workflows offscreen at `1280x720`
- Verified Start button readiness behavior

### License
This project remains open-source under the **MIT License**.

---

Tag: v1.1.0
Release title: v1.1.0 - Extension-Grouped Sorting + Source Refactor
Release notes:
## ImageMerge v1.1.0

Update focused on safer maintainability and deterministic media numbering.

### Highlights
- Refactored the single large `MainApp.py` into a structured `src/media_merge/` package
- Kept `MainApp.py` as the same launch entry point for source and packaged runs
- Added deterministic extension-group sorting before output numbering
- Images are now grouped in this order before numbering: `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.gif`, `.tiff`
- Files inside the same extension group are sorted by numeric filename when possible, including names like `1.png`, `02.png`, `10.png`, and `1(1).jpg`
- Video files still run after image files and now use a deterministic extension order internally
- Fixed CLI processing call after the source split so `python MainApp.py --cli ...` runs correctly
- Windows release now includes a separate portable onefile executable: `ImageMerge-windows-x64-portable.exe`
- Updated executable metadata version to `1.1.0.0`

### Sorting Example
```text
1.png      -> 0001.png
02.png     -> 0002.png
10.png     -> 0003.png
12.png     -> 0004.png
1.jpg      -> 0005.jpg
1(1).jpg   -> 0006.jpg
1.webp     -> 0007.webp
```

### Verification
- `python -m compileall MainApp.py src`
- CLI smoke test for extension-group ordering
- Offscreen PySide6 window construction smoke test

### License
This project remains open-source under the **MIT License**.

---

Tag: v1.0.5
Release title: v1.0.5 - Inside Organizer + Safe Temp Workspace
Release notes:
## ImageMerge v1.0.5

Update focused on expanding organizer workflows, safer processing, and smarter in-place reindex behavior.

### Highlights
- Added new **Inside organizer mode** (`inside_folder`) for organizing media already inside the selected target folder
- Added third workflow page in GUI: Merge / Main Folder / Folder Organizer
- Inside organizer now supports **minimal rename** behavior (keep already-correct sequence names unchanged when possible)
- Gap-fix behavior improved: if sequence has missing indexes (for example `0003` / `0026` missing), files are shifted and reindexed continuously
- Added optional **remove duplicates by content** toggle for inside organizer mode (hash + extension)
- Added optional **Safe temp workspace** toggle (default enabled) for all modes to reduce risk on interruption
- Safe mode now stages processing under `.imagemerge_temp/session-<id>/` and applies final output at completion
- Added CLI flags for new behavior: `--mode inside_folder`, `--remove-duplicates`, and `--no-safe-temp`
- Expanded localization keys for new mode/page/options across supported language files

### License
This project remains open-source under the **MIT License**.

---

Tag: v1.0.4
Release title: v1.0.4 - Main Folder Mode + In-Place Reindex
Release notes:
## ImageMerge v1.0.4

Update focused on adding a workflow for organizing files directly inside the target folder.

### Highlights
- Added new **Main folder mode** (`main_folder`) for in-place organization on the output folder
- Main folder mode now treats the output folder as the primary source and can merge additional input folders into it
- Improved reindex behavior so filenames are reorganized into a continuous sequence after processing
- Existing files already named by ImageMerge pattern (for example `0001.png`) are preserved in ordering logic
- New/mixed filename patterns are still handled by existing sort logic and merged into final sequence
- CLI now supports `--mode main_folder`, and this mode can run without `--input`
- Added UI and localization labels/descriptions for the new mode (EN/TH)

### License
This project remains open-source under the **MIT License**.


### What's New (Microsoft Store Update)
- Added a dedicated **Main Folder page** to separate organizer workflow from merge workflow
- Added optional **Import folders** section inside Main Folder page for selecting extra folders to merge in
- Organizer now processes in this order: organize existing files in main folder first, then merge imports, then re-index final output
- Expanded localization coverage for the new UI keys across all supported languages
- Updated UI theme and button contrast for clearer visibility in grayscale styling

---

Tag: v1.0.3
Release title: v1.0.3 - Multi-Channel Packaging + Store Automation
Release notes:
## ImageMerge v1.0.3

Release focused on distribution expansion, installer coverage, and store automation readiness.

### Highlights
- Added Linux Flatpak packaging pipeline and release artifact output (`.flatpak`)
- Added Linux Snap packaging pipeline and release artifact output (`.snap`)
- Added Linux installer coverage in one release flow: `.deb`, `.rpm`, `.AppImage`, `.flatpak`, `.snap`
- Added Flathub-specific manifest (separate from CI Flatpak manifest) under `packaging/flathub/`
- Added pinned Python dependency module for Flathub (`PySide6` stack with architecture-specific wheel URLs + SHA256)
- Added WinGet automation workflow to submit/update manifests from published releases
- Added Homebrew Cask automation workflow to update cask and open PR to tap repo
- Added project privacy policy document for store listings (`PRIVACY_POLICY.md`, EN + TH)
- Updated macOS release matrix to build both Intel and Apple Silicon artifacts (`macos-13` + `macos-latest`)
- Improved Homebrew automation to support dual-architecture cask output (`on_intel` / `on_arm`) and optional upstream base repo PR flow
- Refined WinGet automation behavior for first-submission vs update flow handling
- Redesigned About dialog to a cleaner scrollable layout for better readability
- Fixed About version display in packaged builds by including `app_metadata.json` in Nuitka build outputs
- Added a dedicated Microsoft Store-oriented Windows MSI variant with product name `ImageMergeGUI` (`ImageMergeGUI-windows-<arch>-msstore.msi`)
- Added automated Windows MSIX packaging + signing in release workflow for Microsoft Store submission (`ImageMergeGUI-windows-<arch>.msix`)

### Packaging / Distribution Notes
- Release workflow now builds additional Linux artifacts and uploads them to GitHub Release automatically
- Flatpak App ID standardized as `me.tamkungz.ImageMerge`
- Snap packaging introduced with strict confinement baseline and desktop integration metadata
- Homebrew workflow targets macOS release zip assets and computes SHA256 during automation
- WinGet workflow targets Windows MSI release assets for manifest submission
- About metadata now stays consistent across source and packaged builds

### Store Readiness Notes
- Microsoft Store and Mac App Store preparation is now supported by accompanying policy/doc updates
- Flathub submission assets are prepared; final Flathub PR still requires Linux-side validation (`flatpak-builder`) and review flow

### License
This project remains open-source under the **MIT License**.

---

Tag: v1.0.2
Release title: v1.0.2 - UI Refresh + Localization Expansion
Release notes:
## ImageMerge v1.0.2

Update focused on UI usability, localization scale-up, and packaging polish.

### Highlights
- Refreshed GUI layout and light theme for better readability
- Improved button/state contrast (including Start during processing)
- Removed hardcoded UI text and fully wired new labels/status strings to locale keys
- Expanded runtime language support from locale files (`ar`, `de`, `en`, `es`, `fr`, `id`, `ja`, `ko`, `ru`, `th`, `vi`, `zh`)
- Improved font selection by language/script with Thai embedded-font priority
- Fixed completion dialog handling to avoid UI freeze after processing finishes
- Updated release ZIP packaging to use a clean top-level `ImageMerge/` folder instead of raw build folder names
- Input folder add flow now keeps default prefix empty unless user edits it

### Packaging Notes
- Release archives now extract into a user-friendly `ImageMerge` directory on all platforms

### License
This project remains open-source under the **MIT License**.

---

Tag: v1.0.1
Release title: v1.0.1 - CLI Mode + Packaging Updates
Release notes:
## ImageMerge v1.0.1

Focused update for command-line workflows and release readiness.

### Highlights
- Added **CLI mode** so ImageMerge can run without opening GUI
- Supports CLI on packaged builds across Windows, Linux, and macOS
- Added repeatable input format: `--input PATH[::PREFIX]`
- Added CLI flags: `--output`, `--mode`, `--clear-output`, `--lang`
- Updated Windows build console behavior to support terminal usage (`attach` mode)
- Updated executable metadata version to `1.0.1.0`

### CLI Example
```bash
ImageMerge --cli --input "/path/a::full" --input "/path/b::short" --output "/path/out" --mode copy_keep
```

### License
This project remains open-source under the **MIT License**.

---

Tag: v1.0.0
Release title: v1.0.0 - PySide6 UI + Nuitka Cross-Platform Build
Release notes:
## ImageMerge v1.0.0

Major update focused on UI modernization, packaging reliability, and release automation.

### Highlights
- Migrated desktop UI to **PySide6**
- Switched build system to **Nuitka**
- Added native build support for:
  - **Windows** (PE `.exe`)
  - **Linux** (ELF binary)
  - **macOS** (Mach-O binary + `.app`)
- Embedded translation system with in-app language selector (EN/TH)
- Embedded app fonts at runtime
- Added executable metadata support via `app_metadata.json`
- Added GitHub Actions workflows:
  - Build test on every push
  - Auto-build + upload release assets on tag

### Build / Packaging Notes
- Default CI build mode is `standalone` for reliability
- Onefile mode can be enabled via environment variable when needed
- Windows code signing is supported by providing PFX configuration in environment variables

### License
This project is open-source under the **MIT License**.

### Checksums
Release asset checksums can be added in a follow-up update for verification.