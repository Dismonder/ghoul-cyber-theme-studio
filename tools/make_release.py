#!/usr/bin/env python3
"""Build the Theme Studio release archive into release/<version>/.

    python3 tools/make_release.py --version v1.0.0

GitHub's own "Source code" zip leaves submodules out, so this archive puts the
app and the theme engine (the theme/ submodule, at its pinned commit) together:

  ghoul-cyber-theme-studio-<version>.zip   ready to run: ThemeStudio.bat / theme-studio.sh
  SHA256SUMS.txt
"""
from __future__ import annotations

import argparse
import hashlib
import io
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENGINE = REPO / "theme"
EXECUTABLE = {"theme-studio.sh"}


def git_zip(repo: Path) -> zipfile.ZipFile:
    """HEAD of a repository as an in-memory zip (honours export-ignore)."""
    data = subprocess.run(["git", "-C", str(repo), "archive", "--format=zip", "HEAD"],
                          capture_output=True, check=True).stdout
    return zipfile.ZipFile(io.BytesIO(data))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", required=True, help="e.g. v1.0.0")
    parser.add_argument("--out", type=Path, default=REPO / "release")
    args = parser.parse_args(argv)
    if not (ENGINE / "build_and_deploy_theme.py").is_file():
        print("theme/ submodule is missing: git submodule update --init", file=sys.stderr)
        return 1
    engine = subprocess.run(["git", "-C", str(ENGINE), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()

    prefix = f"ghoul-cyber-theme-studio-{args.version}"
    out_dir = args.out / args.version
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{prefix}.zip"
    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, sub in ((git_zip(REPO), ""), (git_zip(ENGINE), "theme/")):
            for item in source.infolist():
                if item.is_dir() or (not sub and item.filename.startswith("theme/")):
                    continue
                info = zipfile.ZipInfo(f"{prefix}/{sub}{item.filename}", item.date_time)
                info.compress_type = zipfile.ZIP_DEFLATED
                mode = 0o755 if Path(item.filename).name in EXECUTABLE else 0o644
                info.external_attr = (0o100000 | mode) << 16
                archive.writestr(info, source.read(item))
                count += 1
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (out_dir / "SHA256SUMS.txt").write_text(f"{digest}  {target.name}\n", encoding="utf-8", newline="\n")
    print(f"{target.name}: {count} files, {target.stat().st_size / 1_000_000:.0f} MB, engine {engine}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
