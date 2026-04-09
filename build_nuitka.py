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


def run_cmd(cmd: list[str], cwd: Path, retries: int = 1, retry_cleanup=None):
    print("$", " ".join(cmd))
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

    raise last_error


def normalize_arch(arch_value: str) -> str:
    key = (arch_value or "").strip().lower()
    return ARCH_ALIASES.get(key, key)


def detect_host_arch() -> str:
    machine = platform.machine().strip().lower()
    return normalize_arch(machine)


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
        output_dir / f"{stem}.onefile-build",
        output_dir / f"{stem}.build",
        output_dir / f"{stem}.dist",
        output_dir / f"{APP_NAME}.dist",
        output_dir / f"{APP_NAME}.exe",
        output_dir / APP_NAME,
    ]
    for path in candidates:
        try:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink()
        except Exception:
            pass


def load_app_metadata(root: Path) -> dict[str, str]:
    defaults = {
        "app_name": APP_NAME,
        "company_name": "",
        "product_name": APP_NAME,
        "file_description": APP_NAME,
        "file_version": "1.0.0.0",
        "product_version": "1.0.0.0",
        "copyright": "",
        "icon_ico": "",
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
        if icon_path.exists():
            args.append(f"--windows-icon-from-ico={icon_path}")
        else:
            print(f"Icon not found, skipping icon metadata: {icon_path}")

    return args


def sign_windows_binary(binary_path: Path):
    if os.environ.get("IMAGEMERGE_SIGN", "").strip().lower() not in {"1", "true", "yes", "on"}:
        return

    pfx_path = os.environ.get("IMAGEMERGE_SIGN_PFX", "").strip()
    pfx_password = os.environ.get("IMAGEMERGE_SIGN_PASSWORD", "").strip()
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
    run_cmd(sign_cmd, binary_path.parent)

    verify_cmd = ["signtool", "verify", "/pa", "/v", str(binary_path)]
    run_cmd(verify_cmd, binary_path.parent)


def nuitka_base_cmd(output_dir: Path) -> list[str]:
    return [
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


def try_onefile() -> bool:
    return os.environ.get("IMAGEMERGE_ONEFILE", "").strip().lower() in {"1", "true", "yes", "on"}


def run_build_with_fallback(root: Path, out_dir: Path, onefile_args: list[str], standalone_args: list[str]):
    if try_onefile():
        onefile_cmd = nuitka_base_cmd(out_dir) + onefile_args + [ENTRY_FILE]
        try:
            run_cmd(onefile_cmd, root, retries=2, retry_cleanup=lambda: clean_build_artifacts(out_dir))
            return "onefile"
        except subprocess.CalledProcessError:
            print("Onefile build failed on this environment, falling back to standalone build.")

    standalone_cmd = nuitka_base_cmd(out_dir) + standalone_args + [ENTRY_FILE]
    run_cmd(standalone_cmd, root, retries=2, retry_cleanup=lambda: clean_build_artifacts(out_dir))
    return "standalone"


def build_windows(root: Path):
    out_dir = root / "dist" / "windows"
    metadata = load_app_metadata(root)
    metadata_args = windows_metadata_args(root, metadata)

    mode = run_build_with_fallback(
        root,
        out_dir,
        ["--onefile", "--onefile-no-compression", "--windows-console-mode=attach", *metadata_args],
        ["--windows-console-mode=attach", *metadata_args],
    )
    binary_path = out_dir / (APP_NAME + ".exe")
    if mode == "onefile":
        binary_path = out_dir / (APP_NAME + ".exe")
        print(f"PE build ready: {binary_path}")
    else:
        binary_path = out_dir / (APP_NAME + ".dist") / (APP_NAME + ".exe")
        print(f"PE build ready: {binary_path}")

    sign_windows_binary(binary_path)


def build_linux(root: Path):
    out_dir = root / "dist" / "linux"
    mode = run_build_with_fallback(root, out_dir, ["--onefile", "--onefile-no-compression"], [])
    if mode == "onefile":
        print(f"ELF build ready: {out_dir / APP_NAME}")
    else:
        print(f"ELF build ready: {out_dir / (APP_NAME + '.dist') / APP_NAME}")


def build_macos(root: Path):
    out_bin_dir = root / "dist" / "macos-binary"
    mode = run_build_with_fallback(root, out_bin_dir, ["--onefile", "--onefile-no-compression"], [])

    out_app_dir = root / "dist" / "macos-app"
    app_cmd = nuitka_base_cmd(out_app_dir) + ["--macos-create-app-bundle", ENTRY_FILE]
    run_cmd(app_cmd, root, retries=2, retry_cleanup=lambda: clean_build_artifacts(out_app_dir))

    if mode == "onefile":
        print(f"Mach-O binary ready: {out_bin_dir / APP_NAME}")
    else:
        print(f"Mach-O binary ready: {out_bin_dir / (APP_NAME + '.dist') / APP_NAME}")
    print(f"App bundle ready: {out_app_dir / (APP_NAME + '.app')}")


def main():
    root = Path(__file__).resolve().parent
    system = platform.system().lower()
    host_arch, target_arch = resolve_target_arch()

    print(f"Build host architecture: {host_arch}")
    print(f"Requested target architecture: {target_arch}")

    run_cmd([sys.executable, "generate_embedded_locales.py"], root)

    if system == "windows":
        build_windows(root)
    elif system == "linux":
        build_linux(root)
    elif system == "darwin":
        build_macos(root)
    else:
        raise RuntimeError(f"Unsupported OS: {system}")


if __name__ == "__main__":
    main()
