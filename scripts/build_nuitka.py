import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_NAME = "ImageMerge"
ENTRY_FILE = "MainApp.py"
METADATA_FILE = "app_metadata.json"

ARCH_ALIASES = {
    "x86": "x86",
    "i386": "x86",
    "i686": "x86",
    "x64": "x64",
    "amd64": "x64",
    "x86_64": "x64",
    "arm": "arm",
    "armv7l": "arm",
    "armv6l": "arm",
    "arm64": "arm64",
    "aarch64": "arm64",
}


def run_cmd(
    cmd: list[str],
    cwd: Path,
    retries: int = 1,
    retry_cleanup=None,
    secrets: tuple[str, ...] = (),
):
    shown = " ".join(cmd)
    for secret in secrets:
        if secret:
            shown = shown.replace(secret, "***")
    print("$", shown)
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            subprocess.run(cmd, check=True, cwd=cwd)
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc
            if attempt >= retries:
                break

            print(f"Build attempt {attempt}/{retries} failed, retrying...")
            if retry_cleanup is not None:
                retry_cleanup()
            time.sleep(1.5)

    if last_error is None:
        raise RuntimeError("Command failed without a captured exception")
    if any(secrets):
        raise RuntimeError(
            f"Command failed with exit code {last_error.returncode}: {shown}"
        ) from None
    raise last_error


def normalize_arch(arch_value: str) -> str:
    key = (arch_value or "").strip().lower()
    return ARCH_ALIASES.get(key, key)


def detect_host_arch() -> str:
    machine = normalize_arch(platform.machine())
    if sys.maxsize <= 2**32:
        if machine == "x64":
            return "x86"
        if machine == "arm64":
            return "arm"
    return machine


def resolve_target_arch() -> tuple[str, str]:
    host_arch = detect_host_arch()
    requested = normalize_arch(os.environ.get("IMAGEMERGE_TARGET_ARCH", ""))
    target_arch = requested or host_arch

    if target_arch not in set(ARCH_ALIASES.values()):
        raise RuntimeError(
            f"Unsupported IMAGEMERGE_TARGET_ARCH='{target_arch}'. "
            f"Known targets: {', '.join(sorted(set(ARCH_ALIASES.values())))}"
        )

    if requested and requested != host_arch:
        print(
            f"Requested target arch '{requested}' differs from host arch '{host_arch}'. "
            "Cross-compilation is not configured; build will use host toolchain."
        )

    return host_arch, target_arch


def clean_build_artifacts(output_dir: Path):
    stem = Path(ENTRY_FILE).stem
    candidates = [
        output_dir / f"{stem}.build",
        output_dir / f"{stem}.dist",
        output_dir / f"{APP_NAME}.dist",
        output_dir / f"{APP_NAME}.exe",
        output_dir / APP_NAME,
    ]
    for path in candidates:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def load_app_metadata(root: Path) -> dict[str, str]:
    defaults = {
        "app_name": APP_NAME,
        "company_name": "",
        "product_name": APP_NAME,
        "file_description": APP_NAME,
        "file_version": "2.0.1.0",
        "product_version": "2.0.1.0",
        "copyright": "",
        "icon_ico": "",
        "icon_icns": "",
        "icon_png": "assets/icons/app-icon-1024.png",
    }

    metadata_path = root / METADATA_FILE
    if not metadata_path.exists():
        return defaults

    with open(metadata_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid metadata format in {metadata_path}")

    for key in defaults:
        value = data.get(key, defaults[key])
        defaults[key] = str(value).strip()

    return defaults


def windows_metadata_args(root: Path, metadata: dict[str, str]) -> list[str]:
    args = []

    if metadata["company_name"]:
        args.append(f"--company-name={metadata['company_name']}")
    if metadata["product_name"]:
        args.append(f"--product-name={metadata['product_name']}")
    if metadata["file_description"]:
        args.append(f"--file-description={metadata['file_description']}")
    if metadata["file_version"]:
        args.append(f"--file-version={metadata['file_version']}")
    if metadata["product_version"]:
        args.append(f"--product-version={metadata['product_version']}")
    if metadata["copyright"]:
        args.append(f"--copyright={metadata['copyright']}")

    icon_relative = metadata.get("icon_ico", "")
    if icon_relative:
        icon_path = root / icon_relative
        if not icon_path.is_file():
            raise FileNotFoundError(f"Windows icon not found: {icon_path}")
        args.append(f"--windows-icon-from-ico={icon_path}")

    return args


def resolve_macos_icon(root: Path, metadata: dict[str, str]) -> Path | None:
    icon_candidates: list[Path] = []

    icon_icns = metadata.get("icon_icns", "").strip()
    if icon_icns:
        icon_candidates.append(root / icon_icns)
    for candidate in icon_candidates:
        if candidate.is_file():
            return candidate

    png_relative = metadata.get("icon_png", "assets/icons/app-icon-1024.png").strip()
    if not png_relative:
        return None

    png_source = root / png_relative
    if not png_source.is_file():
        raise FileNotFoundError(f"macOS icon source not found: {png_source}")

    iconset_dir = root / "build" / "ImageMerge.iconset"
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir(parents=True, exist_ok=True)

    iconset_entries = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]

    for file_name, size in iconset_entries:
        run_cmd(
            [
                "sips",
                "-z",
                str(size),
                str(size),
                str(png_source),
                "--out",
                str(iconset_dir / file_name),
            ],
            root,
        )

    generated_icns = root / "build" / "ImageMerge.icns"
    run_cmd(["iconutil", "-c", "icns", str(iconset_dir), "-o", str(generated_icns)], root)
    if not generated_icns.is_file():
        raise FileNotFoundError(f"macOS icon generation did not produce: {generated_icns}")
    return generated_icns


def sign_windows_binary(binary_path: Path):
    if os.environ.get("IMAGEMERGE_SIGN", "").strip().lower() not in {"1", "true", "yes", "on"}:
        return

    pfx_path = os.environ.get("IMAGEMERGE_SIGN_PFX", "").strip()
    pfx_password = os.environ.get("IMAGEMERGE_SIGN_PASSWORD", "")
    timestamp_url = os.environ.get("IMAGEMERGE_SIGN_TIMESTAMP", "http://timestamp.digicert.com").strip()

    if not pfx_path or not pfx_password:
        raise RuntimeError("Signing requested but IMAGEMERGE_SIGN_PFX / IMAGEMERGE_SIGN_PASSWORD not set")

    sign_cmd = [
        "signtool",
        "sign",
        "/fd",
        "SHA256",
        "/f",
        pfx_path,
        "/p",
        pfx_password,
        "/tr",
        timestamp_url,
        "/td",
        "SHA256",
        str(binary_path),
    ]
    run_cmd(sign_cmd, binary_path.parent, secrets=(pfx_password,))

    verify_cmd = ["signtool", "verify", "/pa", "/v", str(binary_path)]
    run_cmd(verify_cmd, binary_path.parent)


def nuitka_base_cmd(root: Path, output_dir: Path) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--remove-output",
        "--enable-plugin=pyside6",
        f"--output-dir={output_dir}",
        f"--output-filename={APP_NAME}",
    ]

    metadata_path = root / METADATA_FILE
    if metadata_path.exists():
        cmd.append(f"--include-data-file={metadata_path}=app_metadata.json")

    font_dir = root / "build" / "fonts"
    font_files = sorted(font_dir.glob("*.ttf"))
    font_licenses = sorted(font_dir.glob("*-OFL.txt"))
    if len(font_files) != 6 or len(font_licenses) != 6:
        raise FileNotFoundError(f"Downloaded Noto Sans fonts and licenses not found in {font_dir}")
    cmd.append(f"--include-data-dir={font_dir}=fonts")

    return cmd


def binary_only() -> bool:
    return os.environ.get("IMAGEMERGE_BINARY_ONLY", "").strip().lower() in {"1", "true", "yes", "on"}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)


def build_windows(root: Path):
    out_dir = root / "dist" / "windows"
    reset_output_dir(out_dir)
    metadata = load_app_metadata(root)
    metadata_args = windows_metadata_args(root, metadata)
    standalone_cmd = nuitka_base_cmd(root, out_dir) + [
        "--windows-console-mode=attach",
        *metadata_args,
        ENTRY_FILE,
    ]
    run_cmd(standalone_cmd, root, retries=2, retry_cleanup=lambda: clean_build_artifacts(out_dir))

    binary_path = out_dir / f"{Path(ENTRY_FILE).stem}.dist" / f"{APP_NAME}.exe"
    if not binary_path.is_file():
        raise FileNotFoundError(f"Windows build did not produce: {binary_path}")
    print(f"PE standalone folder build ready: {binary_path}")

    sign_windows_binary(binary_path)


def build_linux(root: Path):
    if shutil.which("patchelf") is None:
        raise RuntimeError("Missing required tool 'patchelf'. Install it first (Ubuntu/Debian: sudo apt install -y patchelf)")

    out_dir = root / "dist" / "linux"
    reset_output_dir(out_dir)
    standalone_cmd = nuitka_base_cmd(root, out_dir) + [ENTRY_FILE]
    run_cmd(standalone_cmd, root, retries=2, retry_cleanup=lambda: clean_build_artifacts(out_dir))

    binary_path = out_dir / f"{Path(ENTRY_FILE).stem}.dist" / APP_NAME
    if not binary_path.is_file():
        raise FileNotFoundError(f"Linux build did not produce: {binary_path}")
    print(f"ELF standalone build ready: {binary_path}")


def build_macos(root: Path):
    out_bin_dir = root / "dist" / "macos-binary"
    reset_output_dir(out_bin_dir)
    metadata = load_app_metadata(root)

    standalone_cmd = nuitka_base_cmd(root, out_bin_dir) + [ENTRY_FILE]
    run_cmd(standalone_cmd, root, retries=2, retry_cleanup=lambda: clean_build_artifacts(out_bin_dir))

    binary_path = out_bin_dir / f"{Path(ENTRY_FILE).stem}.dist" / APP_NAME
    if not binary_path.is_file():
        raise FileNotFoundError(f"macOS build did not produce: {binary_path}")
    print(f"Mach-O standalone build ready: {binary_path}")

    if binary_only():
        print("Binary-only mode enabled; skipping macOS .app bundle build.")
        return

    out_app_dir = root / "dist" / "macos-app"
    reset_output_dir(out_app_dir)
    app_cmd = nuitka_base_cmd(root, out_app_dir) + [
        "--macos-create-app-bundle",
        f"--macos-app-name={APP_NAME}",
    ]

    macos_icon = resolve_macos_icon(root, metadata)
    if macos_icon is not None:
        app_cmd.append(f"--macos-app-icon={macos_icon}")
    else:
        print("macOS icon not found; building app bundle without custom .icns")

    app_cmd.append(ENTRY_FILE)
    run_cmd(app_cmd, root, retries=2, retry_cleanup=lambda: clean_build_artifacts(out_app_dir))

    app_candidates = sorted(p for p in out_app_dir.glob("*.app") if p.is_dir())
    if not app_candidates:
        raise FileNotFoundError(
            f"macOS app bundle build did not produce any .app in: {out_app_dir}"
        )
    produced_bundle = app_candidates[0]
    app_bundle = out_app_dir / f"{APP_NAME}.app"
    if produced_bundle != app_bundle:
        if app_bundle.exists():
            shutil.rmtree(app_bundle)
        produced_bundle.rename(app_bundle)
        print(f"Renamed {produced_bundle.name} -> {app_bundle.name}")
    if not app_bundle.is_dir():
        raise FileNotFoundError(f"macOS app bundle build did not produce: {app_bundle}")
    print(f"App bundle ready: {app_bundle}")


def clean_generated_build_files(root: Path) -> None:
    package_dir = root / "src" / "media_merge"
    for generated_module in ("_embedded_locales.py", "_embedded_fonts.py"):
        (package_dir / generated_module).unlink(missing_ok=True)

    for generated_path in (
        root / "build" / "fonts",
        root / "build" / "ImageMerge.iconset",
    ):
        if generated_path.is_dir():
            shutil.rmtree(generated_path)

    generated_icns = root / "build" / "ImageMerge.icns"
    generated_icns.unlink(missing_ok=True)

    for output_name in ("windows", "linux", "macos-binary", "macos-app"):
        output_dir = root / "dist" / output_name
        cache_path = output_dir / f"{Path(ENTRY_FILE).stem}.build"
        if cache_path.is_dir():
            shutil.rmtree(cache_path)

    build_dir = root / "build"
    if build_dir.is_dir():
        try:
            build_dir.rmdir()
        except OSError:
            pass


def main():
    root = Path(__file__).resolve().parents[1]
    system = platform.system().lower()
    host_arch, target_arch = resolve_target_arch()

    print(f"Build host architecture: {host_arch}")
    print(f"Target architecture: {target_arch}")

    try:
        run_cmd(
            [sys.executable, str(root / "scripts" / "generate_embedded_locales.py")],
            root,
        )
        run_cmd(
            [sys.executable, str(root / "scripts" / "prepare_embedded_fonts.py")],
            root,
            retries=3,
        )

        if system == "windows":
            build_windows(root)
        elif system == "linux":
            build_linux(root)
        elif system == "darwin":
            build_macos(root)
        else:
            raise RuntimeError(f"Unsupported OS: {system}")
    finally:
        clean_generated_build_files(root)


if __name__ == "__main__":
    main()