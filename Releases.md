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
