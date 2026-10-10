import argparse
import email.utils
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


SUPPORTED_SUITES = {"jammy": "22.04", "noble": "24.04", "resolute": "26.04"}


def is_inside(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def extract_runtime(archive: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zip_file:
        members = zip_file.infolist()
        for member in members:
            target = (destination / member.filename).resolve()
            if not is_inside(target, root):
                raise ValueError(f"Unsafe path in runtime archive: {member.filename}")
            
        for member in members:
            target = destination / member.filename
            mode = (member.external_attr >> 16) & 0o7777
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if stat.S_ISLNK((member.external_attr >> 16) & 0xFFFF):
                link_target = zip_file.read(member).decode("utf-8")
                link_path = (target.parent / link_target).resolve()
                if not is_inside(link_path, root):
                    raise ValueError(f"Unsafe symlink in runtime archive: {member.filename}")
                target.unlink(missing_ok=True)
                os.symlink(link_target, target)
                continue
            with zip_file.open(member) as source, open(target, "wb") as output:
                shutil.copyfileobj(source, output)
            if mode:
                target.chmod(mode | stat.S_IRUSR | stat.S_IWUSR)

    runtime_dir = destination / "ImageMerge"
    binary = runtime_dir / "ImageMerge"
    if not binary.is_file():
        raise FileNotFoundError(f"Standalone ImageMerge executable not found in {archive}")
    binary.chmod(binary.stat().st_mode | 0o755)

    missing = [
        member.filename
        for member in members
        if not member.is_dir() and not (destination / member.filename).is_symlink()
        and not (destination / member.filename).is_file()
    ]
    if missing:
        raise FileNotFoundError(f"Runtime files missing after extraction: {missing[:5]}")
    return runtime_dir


def build_source_package(
    root: Path,
    archive: Path,
    tag: str,
    suite: str,
    output_dir: Path,
    signing_key: str,
    signing_command: Path,
    maintainer_email: str,
) -> Path:
    if suite not in SUPPORTED_SUITES:
        raise ValueError(
            f"Unsupported Ubuntu series {suite!r}; choose one of {sorted(SUPPORTED_SUITES)}"
        )
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError(f"Invalid release tag: {tag}")
    if not signing_key.strip():
        raise ValueError("A GPG signing key ID is required")
    parsed_name, parsed_email = email.utils.parseaddr(maintainer_email)
    if (
        parsed_name
        or parsed_email != maintainer_email
        or not re.fullmatch(r"[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+", parsed_email)
    ):
        raise ValueError("Maintainer email must be a plain email address")

    upstream_version = tag[1:]
    metadata = json.loads((root / "app_metadata.json").read_text(encoding="utf-8"))
    metadata_version = str(metadata.get("product_version", "")).rsplit(".", 1)[0]
    if metadata_version != upstream_version:
        raise ValueError(
            f"Tag version {upstream_version} does not match app metadata version {metadata_version}"
        )

    debian_version = f"{upstream_version}ubuntu{SUPPORTED_SUITES[suite]}.1"
    output_dir.mkdir(parents=True, exist_ok=True)
    template_dir = root / "packaging" / "launchpad" / "debian"
    package_dir_name = f"imagemerge-{debian_version}"

    with tempfile.TemporaryDirectory(prefix="imagemerge-launchpad-", dir=output_dir) as temp_name:
        work_dir = Path(temp_name)
        package_dir = work_dir / package_dir_name
        package_dir.mkdir()
        runtime_dir = extract_runtime(archive, work_dir / "extract")
        shutil.copytree(runtime_dir, package_dir / "runtime" / "ImageMerge")
        shutil.copy2(root / "README.md", package_dir / "README.md")
        shutil.copy2(root / "LICENSE", package_dir / "LICENSE")
        shutil.copytree(template_dir, package_dir / "debian")
        control_file = package_dir / "debian" / "control"
        control_file.write_text(
            control_file.read_text(encoding="utf-8").replace(
                "__LAUNCHPAD_MAINTAINER_EMAIL__",
                maintainer_email,
            ),
            encoding="utf-8",
        )
        (package_dir / "packaging").mkdir()
        shutil.copy2(
            root / "packaging" / "launchpad" / "imagemerge",
            package_dir / "packaging" / "imagemerge",
        )

        changelog = (
            f"imagemerge ({debian_version}) {suite}; urgency=medium\n\n"
            f"  * Package ImageMerge {upstream_version} for Ubuntu {suite}.\n\n"
            f" -- TamKungZ_ <{maintainer_email}>  "
            f"{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}\n"
        )
        (package_dir / "debian" / "changelog").write_text(changelog, encoding="utf-8")
        (package_dir / "debian" / "rules").chmod(0o755)
        (package_dir / "packaging" / "imagemerge").chmod(0o755)

        subprocess.run(
            [
                "dpkg-buildpackage",
                "-S",
                "-sa",
                f"-k{signing_key}",
                f"-p{signing_command}",
            ],
            cwd=package_dir,
            check=True,
        )

        changes_files = list(work_dir.glob("*_source.changes"))
        if len(changes_files) != 1:
            raise FileNotFoundError(f"Expected one source .changes file, found {len(changes_files)}")
        changes_file = changes_files[0]
        for artifact in work_dir.iterdir():
            if artifact.is_file() and artifact.suffix in {".changes", ".dsc", ".xz", ".buildinfo"}:
                shutil.copy2(artifact, output_dir / artifact.name)
        return output_dir / changes_file.name


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a Launchpad PPA source upload from a release bundle."
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--suite", required=True, choices=sorted(SUPPORTED_SUITES))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--signing-key", required=True)
    parser.add_argument("--signing-command", type=Path, required=True)
    parser.add_argument("--maintainer-email", required=True)
    args = parser.parse_args()

    changes_file = build_source_package(
        args.root.resolve(),
        args.archive.resolve(),
        args.tag,
        args.suite,
        args.output_dir.resolve(),
        args.signing_key,
        args.signing_command.resolve(),
        args.maintainer_email,
    )
    print(f"Source package ready: {changes_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())