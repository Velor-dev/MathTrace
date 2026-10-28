"""Check staged Python bytes without changing the index or working tree."""

from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def main() -> int:
    os.chdir(os.fsdecode(git("rev-parse", "--show-toplevel")).strip())
    if git("diff", "--cached", "--name-only", "--diff-filter=U", "-z"):
        print("pre-commit: resolve staged merge conflicts first", file=sys.stderr)
        return 1
    names = git(
        "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z", "--", "*.py", "*.pyi"
    )
    paths = [os.fsdecode(name) for name in names.split(b"\0") if name]
    if not paths:
        return 0
    lock = tomllib.loads(git("show", ":uv.lock").decode("utf-8"))
    expected = next(package["version"] for package in lock["package"] if package["name"] == "ruff")
    try:
        installed = version("ruff")
    except PackageNotFoundError:
        installed = None
    if installed != expected:
        print(
            "pre-commit: install locked Ruff with uv sync --locked --only-group quality --inexact",
            file=sys.stderr,
        )
        return 1
    # Staged configuration and file contents matter, not unstaged edits.
    config = git("show", ":pyproject.toml")
    with tempfile.TemporaryDirectory(prefix="mathtrace-ruff-") as temporary:
        config_path = Path(temporary) / "pyproject.toml"
        config_path.write_bytes(config)
        failed = False
        for path in paths:
            source = git("show", ":" + path)
            for operation in (["check", "--no-cache"], ["format", "--check", "--no-cache"]):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "ruff",
                        *operation,
                        "--config",
                        str(config_path),
                        "--stdin-filename",
                        path,
                        "-",
                    ],
                    input=source,
                )
                failed |= result.returncode != 0
        if failed:
            print(
                "pre-commit: fix the reported files, review your edits, then git add them again. "
                "No files were changed by this hook.",
                file=sys.stderr,
            )
        return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
