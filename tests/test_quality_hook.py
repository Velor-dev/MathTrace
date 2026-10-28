"""Staged-only hook regressions in disposable Git repositories."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QualityHookTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mathtrace quality ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run_git("init", "-q")
        for name in ("pyproject.toml", "uv.lock", "tools/check_staged.py", ".githooks/pre-commit"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        self.run_git("add", "pyproject.toml", "uv.lock")

    def run_git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def check(self, expected):
        before = self.run_git("write-tree").stdout
        contents = {
            p: p.read_bytes() for p in self.root.rglob("*") if p.is_file() and ".git" not in p.parts
        }
        result = subprocess.run(
            [sys.executable, str(self.root / "tools/check_staged.py")],
            cwd=self.root,
            capture_output=True,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual(self.run_git("write-tree").stdout, before)
        self.assertTrue(all(p.read_bytes() == content for p, content in contents.items()))

    def stage(self, content):
        (self.root / "file with spaces.py").write_text(content)
        self.run_git("add", "file with spaces.py")

    def test_good_staged_bytes_ignore_bad_worktree_and_config(self):
        self.stage("value = 1\n")
        (self.root / "file with spaces.py").write_text("value=undefined\n")
        (self.root / "pyproject.toml").write_text("invalid config")
        self.check(0)

    def test_bad_staged_bytes_are_not_hidden_by_good_worktree(self):
        self.stage("value = undefined\n")
        (self.root / "file with spaces.py").write_text("value = 1\n")
        self.check(1)

    def test_formatting_and_syntax_fail_without_fixes(self):
        for source in ("value=1\n", "def broken(:\n"):
            with self.subTest(source=source):
                self.stage(source)
                self.check(1)

    def test_docs_only_and_deleted_python_skip_ruff(self):
        (self.root / "note.md").write_text("docs only")
        self.run_git("add", "note.md")
        self.check(0)
        self.stage("value = undefined\n")
        (self.root / "file with spaces.py").unlink()
        self.run_git("add", "-u")
        self.check(0)

    def test_renamed_python_is_checked(self):
        self.stage("value = 1\n")
        self.run_git("mv", "file with spaces.py", "renamed.py")
        (self.root / "renamed.py").write_text("value = undefined\n")
        self.run_git("add", "renamed.py")
        self.check(1)

    def test_actual_git_hook_runs_offline(self):
        self.stage("value = 1\n")
        self.run_git("config", "core.hooksPath", ".githooks")
        environment = dict(os.environ, UV_PROJECT_ENVIRONMENT=str(Path(sys.prefix)))
        result = subprocess.run(
            ["git", "hook", "run", "pre-commit"],
            cwd=self.root,
            env=environment,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.stage("value = undefined\n")
        result = subprocess.run(
            ["git", "hook", "run", "pre-commit"],
            cwd=self.root,
            env=environment,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_wrong_installed_ruff_version_fails_closed(self):
        self.stage("value = 1\n")
        import re

        lock = self.root / "uv.lock"
        text = lock.read_text()
        text = re.sub(r'(name = "ruff"\nversion = ")[^"]+', r'\g<1>0.0.0', text)
        lock.write_text(text)
        self.run_git("add", "uv.lock")
        self.check(1)
