import argparse
import email.utils
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


SUPPORTED_SUITES = {"jammy": "22.04", "noble": "24.04", "resolute": "26.04"}

REQUIRED_RUNTIME_DEPENDS = [
    "libxcb-cursor0",
    "libxkbcommon-x11-0",
    "libxkbcommon0",
    "libxcb1",
    "libxcb-icccm4",
    "libxcb-keysyms1",
    "libxcb-randr0",
    "libxcb-shape0",
    "libxcb-xfixes0",
    "libxcb-xinerama0",
    "libxcb-xkb1",
    "libxcb-sync1",
    "libxcb-shm0",
    "libxcb-render0",
    "libxcb-render-util0",
    "libxcb-image0",
    "libx11-xcb1",
    "libx11-6",
    "libxext6",
    "libxrender1",
    "libxi6",
    "libsm6",
    "libice6",
    "libegl1",
    "libgl1",
    "libfontconfig1",
    "libfreetype6",
    "libdbus-1-3",
    "libglib2.0-0",
    "zlib1g",
]


def merge_runtime_depends(control_text: str, required: list[str]) -> str:
    """Add `required` packages to the Depends field of the first binary package stanza."""
    lines = control_text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.startswith("Package:")), None)
    if start is None:
        raise ValueError("debian/control has no binary Package stanza")
    end = start
    while end < len(lines) and lines[end].strip():
        end += 1

    dep_start = next((i for i in range(start, end) if lines[i].startswith("Depends:")), None)
    existing: list[str] = []
    dep_end = dep_start
    if dep_start is not None:
        dep_end = dep_start + 1
        while dep_end < end and lines[dep_end][:1] in (" ", "\t"):
            dep_end += 1
        joined = " ".join(
            [lines[dep_start][len("Depends:"):]] + [l.strip() for l in lines[dep_start + 1:dep_end]]
        )
        existing = [item.strip() for item in joined.split(",") if item.strip()]

    def name_of(entry: str) -> str:
        return re.split(r"[\s(|<\[]", entry, maxsplit=1)[0]

    present = {name_of(item) for item in existing}
    merged = existing + [pkg for pkg in required if pkg not in present]
    block = ["Depends: " + merged[0] + ","] + [f" {item}," for item in merged[1:]]
    block[-1] = block[-1].rstrip(",")

    if dep_start is None:
        arch = next((i for i in range(start, end) if lines[i].startswith("Architecture:")), end - 1)
        lines[arch + 1:arch + 1] = block
    else:
        lines[dep_start:dep_end] = block
    return "\n".join(lines)


def is_inside(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def normalize_line_endings(*paths: Path) -> None:
    crlf = bytes((0x0D, 0x0A))
    lf = bytes((0x0A,))
    for root in paths:
        if root.is_dir():
            candidates = [root, *root.rglob("*")]
        else:
            candidates = [root]
        for path in candidates:
            if not path.is_file() or path.is_symlink():
                continue
            data = path.read_bytes()
            if crlf in data:
                path.write_bytes(data.replace(crlf, lf))


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
    revision: int = 1,
    changelog_note: str = "",
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

    if revision < 1:
        raise ValueError("Revision must be 1 or greater")
    debian_version = f"{upstream_version}ubuntu{SUPPORTED_SUITES[suite]}.{revision}"
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
        control_text = control_file.read_text(encoding="utf-8").replace(
            "__LAUNCHPAD_MAINTAINER_EMAIL__",
            maintainer_email,
        )
        control_text = merge_runtime_depends(control_text, REQUIRED_RUNTIME_DEPENDS)
        control_file.write_text(control_text, encoding="utf-8")
        for dependency in REQUIRED_RUNTIME_DEPENDS:
            if dependency not in control_file.read_text(encoding="utf-8"):
                raise RuntimeError(f"debian/control is missing dependency {dependency}")
        (package_dir / "packaging").mkdir()
        shutil.copy2(
            root / "packaging" / "launchpad" / "imagemerge",
            package_dir / "packaging" / "imagemerge",
        )
        normalize_line_endings(package_dir / "debian", package_dir / "packaging")

        note = " ".join(changelog_note.split())
        note_line = f"  * {note}\n" if note else ""
        changelog = (
            f"imagemerge ({debian_version}) {suite}; urgency=medium\n\n"
            f"  * Package ImageMerge {upstream_version} for Ubuntu {suite}.\n"
            f"{note_line}\n"
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
                "-I.imagemerge-keep-everything",
                f"-k{signing_key}",
                f"-p{signing_command}",
            ],
            cwd=package_dir,
            check=True,
        )

        source_tarballs = list(work_dir.glob("*.tar.xz"))
        if len(source_tarballs) != 1:
            raise FileNotFoundError(
                f"Expected one source tarball, found {len(source_tarballs)}"
            )
        expected = sum(
            1
            for path in (package_dir / "runtime").rglob("*")
            if path.is_file() and not path.is_symlink()
        )
        with tarfile.open(source_tarballs[0]) as tar_file:
            packed = sum(
                1
                for member in tar_file.getmembers()
                if member.isfile() and "/runtime/" in member.name
            )
        if packed != expected:
            raise RuntimeError(
                f"Source tarball holds {packed} runtime files but the runtime has "
                f"{expected}; refusing to upload an incomplete package"
            )

        changes_files = list(work_dir.glob("*_source.changes"))
        if len(changes_files) != 1:
            raise FileNotFoundError(
                f"Expected one source .changes file, found {len(changes_files)}"
            )
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
    parser.add_argument(
        "--revision",
        type=int,
        default=1,
        help="Ubuntu package revision (the trailing .N in 2.0.3ubuntu26.04.N); "
        "raise it to re-upload the same release with packaging fixes",
    )
    parser.add_argument("--changelog-note", default="", help="Extra changelog line")
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
        args.revision,
        args.changelog_note,
    )
    print(f"Source package ready: {changes_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())