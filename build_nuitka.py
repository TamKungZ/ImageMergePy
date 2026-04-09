import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_NAME = "ImageMerge"
ENTRY_FILE = "MainApp.py"


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
    mode = run_build_with_fallback(
        root,
        out_dir,
        ["--onefile", "--onefile-no-compression", "--windows-console-mode=disable"],
        ["--windows-console-mode=disable"],
    )
    if mode == "onefile":
        print(f"PE build ready: {out_dir / (APP_NAME + '.exe')}")
    else:
        print(f"PE build ready: {out_dir / (APP_NAME + '.dist') / (APP_NAME + '.exe')}")


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
