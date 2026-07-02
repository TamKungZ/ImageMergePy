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
