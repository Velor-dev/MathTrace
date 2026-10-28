"""Provision and verify an official pinned Lean distribution.

The trust root is the official GitHub release API over TLS and its asset digest,
not an executable's self-reported --version output. No arbitrary checker path is
accepted by the formal runner.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import stat
import sys
import tempfile
import time
import uuid
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from .store import StateError, digest


class DownloadProgress:
    """Format and stream download progress to stderr without polluting stdout."""

    def __init__(self, total_bytes: int | None = None, stream=None, label: str = 'Lean 4'):
        self.total_bytes = total_bytes if (total_bytes and total_bytes > 0) else None
        self.transferred = 0
        self.stream = stream or sys.stderr
        self.label = label
        self.start_time = time.monotonic()
        self.last_update = 0.0
        self.is_tty = hasattr(self.stream, 'isatty') and self.stream.isatty()
        self.last_pct_bucket = -1

    def update(self, chunk_len: int, force: bool = False):
        self.transferred += chunk_len
        now = time.monotonic()
        if not force and (now - self.last_update < 0.1):
            return
        self.last_update = now
        elapsed = max(now - self.start_time, 0.001)
        speed = self.transferred / elapsed

        mb_transferred = self.transferred / (1024 * 1024)
        mb_speed = speed / (1024 * 1024)

        if self.total_bytes:
            mb_total = self.total_bytes / (1024 * 1024)
            pct = min(int((self.transferred / self.total_bytes) * 100), 100)
            eta = max(0, int((self.total_bytes - self.transferred) / max(speed, 1)))
            eta_str = f"{eta // 60:02d}:{eta % 60:02d}"

            if self.is_tty:
                bar_width = 24
                filled = int(bar_width * pct / 100)
                try:
                    bar = '█' * filled + '░' * (bar_width - filled)
                    text = f"\r   [{bar}] {pct:3d}% ({mb_transferred:5.1f} MB / {mb_total:5.1f} MB) {mb_speed:4.1f} MB/s [{eta_str}]"
                    self.stream.write(text)
                except UnicodeEncodeError:
                    bar = '=' * filled + '-' * (bar_width - filled)
                    text = f"\r   [{bar}] {pct:3d}% ({mb_transferred:5.1f} MB / {mb_total:5.1f} MB) {mb_speed:4.1f} MB/s [{eta_str}]"
                    self.stream.write(text)
                self.stream.flush()
            else:
                bucket = pct // 20
                if bucket != self.last_pct_bucket or force:
                    self.last_pct_bucket = bucket
                    self.stream.write(f"-> Downloading {self.label}: {pct}% ({mb_transferred:.1f} MB / {mb_total:.1f} MB) at {mb_speed:.1f} MB/s\n")
                    self.stream.flush()
        else:
            if self.is_tty:
                text = f"\r   Downloading {self.label}: {mb_transferred:5.1f} MB ({mb_speed:4.1f} MB/s)"
                self.stream.write(text)
                self.stream.flush()
            else:
                if now - self.last_update >= 5.0 or force:
                    self.stream.write(f"-> Downloading {self.label}: {mb_transferred:.1f} MB ({mb_speed:.1f} MB/s)\n")
                    self.stream.flush()

    def finish(self):
        self.update(0, force=True)
        mb_total = (self.total_bytes or self.transferred) / (1024 * 1024)
        if self.is_tty:
            try:
                self.stream.write(f"\r   [✓] Downloaded {self.label} ({mb_total:.1f} MB)\n")
            except UnicodeEncodeError:
                self.stream.write(f"\r   [OK] Downloaded {self.label} ({mb_total:.1f} MB)\n")
        else:
            self.stream.write(f"-> Downloaded {self.label} ({mb_total:.1f} MB)\n")
        self.stream.flush()


def _emit_status(message: str, stream=None) -> None:
    target = stream or sys.stderr
    try:
        target.write(message)
    except UnicodeEncodeError:
        target.write(message.replace('✓', 'OK'))
    target.flush()


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_toolchain(record: dict) -> dict:
    data = record['data']
    root = Path(data['root']).resolve()
    actual = {}
    for path in root.rglob('*'):
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise StateError('Redirected path in pinned Lean toolchain')
        if path.is_file():
            actual[path.relative_to(root).as_posix()] = path
    if set(actual) != set(data['files']):
        raise StateError('Pinned Lean toolchain file set changed or is missing')
    for name, expected in data['files'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha256(path) != expected:
            raise StateError('Pinned Lean toolchain contents changed or are missing')
    executable = (root / data['executable']).resolve()
    if not executable.is_relative_to(root) or data['executable'] not in data['files']:
        raise StateError('Invalid Lean executable identity')
    return {'executable': str(executable), 'root': str(root), 'files': data['files'],
            'platform': data['platform'], 'release_digest': data['release_digest']}


def extract_distribution(archive: Path, directory: Path, expected_digest: str, *,
                         target_platform: str | None = None, stream=None) -> tuple[Path, dict, str]:
    """Publish a new verified tree without merging into any prior installation."""
    directory = directory.resolve()
    with tempfile.TemporaryDirectory(prefix='.lean-stage-', dir=directory) as temporary:
        staged = Path(temporary).resolve()
        if staged.parent != directory:
            raise StateError('Toolchain stage escaped its installation directory')
        expected_files = {}
        destinations = set()
        with zipfile.ZipFile(archive) as package:
            infolist = package.infolist()
            file_count = sum(1 for item in infolist if not item.is_dir())
            _emit_status(f"-> Extracting Lean distribution ({file_count:,} files)...\n", stream=stream)
            for item in infolist:
                relative = PurePosixPath(item.filename)
                destination = (staged / relative.as_posix()).resolve()
                key = relative.as_posix().rstrip('/')
                # Avoid platform-specific rewrites/aliases during extraction.
                invalid_component = any(part.rstrip('. ') != part or any(c in part for c in '<>:"|?*')
                                        for part in relative.parts)
                if (relative.is_absolute() or '..' in relative.parts or '\\' in item.filename
                        or invalid_component or not key or key == '.'
                        or not destination.is_relative_to(staged) or stat.S_ISLNK(item.external_attr >> 16)):
                    raise StateError('Unsafe path or symlink in Lean distribution')
                collision_key = key.casefold() if sys.platform == 'win32' else key
                if collision_key in destinations:
                    raise StateError('Duplicate or aliased path in Lean distribution')
                destinations.add(collision_key)
                if not item.is_dir():
                    with package.open(item) as source:
                        expected_files[key] = hashlib.file_digest(source, 'sha256').hexdigest()
            package.extractall(staged)
        windows = target_platform == 'windows' if target_platform else sys.platform == 'win32'
        if not windows and sys.platform != 'win32':
            with zipfile.ZipFile(archive) as package:
                for item in package.infolist():
                    if not item.is_dir() and (item.external_attr >> 16) & 0o111:
                        (staged / item.filename).chmod(0o755)
            for binary in staged.rglob('bin/*'):
                if binary.is_file():
                    binary.chmod(0o755)
        _emit_status("-> Verifying toolchain integrity against archive manifest...\n", stream=stream)
        actual_files = {p.relative_to(staged).as_posix(): p for p in staged.rglob('*') if p.is_file()}
        if set(actual_files) != set(expected_files):
            raise StateError('Extracted Lean file set differs from the verified archive')
        if any(sha256(actual_files[name]) != hashed for name, hashed in expected_files.items()):
            raise StateError('Extracted Lean bytes differ from the verified archive')
        if sha256(archive) != expected_digest:
            raise StateError('Lean archive changed during extraction')
        windows = target_platform == 'windows' if target_platform else sys.platform == 'win32'
        binaries = [p for p in actual_files.values()
                    if p.name == ('lean.exe' if windows else 'lean') and p.parent.name == 'bin']
        if len(binaries) != 1:
            raise StateError('Ambiguous Lean executable in verified archive')
        relative_root = binaries[0].parent.parent.relative_to(staged)
        toolchain_root = staged / relative_root
        if any(not path.is_relative_to(toolchain_root) for path in actual_files.values()):
            raise StateError('Lean archive contains files outside the selected distribution root')
        files = {path.relative_to(toolchain_root).as_posix(): expected_files[name]
                 for name, path in actual_files.items()}
        _emit_status("   [✓] Verified toolchain integrity\n", stream=stream)
        # A unique destination leaves existing installed versions and records
        # intact. Same-parent rename atomically publishes the complete tree.
        installed = directory / ('distribution-' + uuid.uuid4().hex)
        staged.rename(installed)
        return installed / relative_root, files, digest(expected_files)


class Toolchains:
    def __init__(self, store):
        self.store = store

    def install_lean(self, version: str, *, execution_mode: str | None = None, stream=None) -> str:
        if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-rc\d+)?', version):
            raise StateError('Specify an exact Lean release tag, not latest')
        marker, target = execution_target(execution_mode)
        url = f'https://api.github.com/repos/leanprover/lean4/releases/tags/{version}'
        request = urllib.request.Request(url, headers={'User-Agent': 'MathTrace', 'Accept': 'application/vnd.github+json'})
        with urllib.request.urlopen(request, timeout=60) as response:
            release = json.load(response)
        candidates = [a for a in release.get('assets', []) if a['name'].endswith(f'-{marker}.zip')]
        if len(candidates) != 1:
            raise StateError('No unambiguous official ZIP distribution for this platform; do not substitute an unchecked binary')
        asset = candidates[0]
        expected = asset.get('digest', '')
        if not isinstance(expected,str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', expected):
            raise StateError('Publisher asset digest unavailable; refusing an unverified toolchain')
        download = asset['browser_download_url']
        if not download.startswith(f'https://github.com/leanprover/lean4/releases/download/{version}/'):
            raise StateError('Unexpected toolchain publisher URL')
        directory = self.store.path.parent / 'toolchains' / version
        directory.mkdir(parents=True, exist_ok=True)
        archive = directory / asset['name']
        if not archive.is_file() or sha256(archive) != expected.split(':')[1]:
            with urllib.request.urlopen(download, timeout=120) as response, archive.open('wb') as output:
                headers = getattr(response, 'headers', None)
                content_length = headers.get('Content-Length') if headers else None
                total_bytes = int(content_length) if (content_length and content_length.isdigit()) else None
                progress = DownloadProgress(total_bytes, label=f'Lean {version}', stream=stream)
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    progress.update(len(chunk))
                progress.finish()
        if sha256(archive) != expected.split(':')[1]:
            raise StateError('Lean distribution digest mismatch')
        root, files, archive_file_set_hash = extract_distribution(archive, directory, expected.split(':')[1],
                                                                  target_platform=marker, stream=stream)
        executable = 'bin/lean.exe' if marker == 'windows' else 'bin/lean'
        with self.store.transaction():
            identifier = self.store.put('toolchain', {'root': str(root.resolve()),
                'executable': executable, 'files': files,
                'version': version, 'publisher_metadata': url, 'release_digest': expected,
                'archive': str(archive.resolve()), 'platform': target,
                'installation_layout': 'fresh-archive-exact-versioned-tree',
                'archive_file_set_hash': archive_file_set_hash})
            self.store.decide(identifier, 'installed', {'reason': 'Official publisher asset digest and complete distribution manifest verified'})
            return identifier


def execution_target(execution_mode=None):
    from .backend import mode
    selected = mode(execution_mode)
    architecture = platform.machine().lower()
    architecture = {'amd64': 'x86_64', 'arm64': 'aarch64'}.get(architecture, architecture)
    if selected == 'bubblewrap':
        if architecture != 'x86_64':
            raise StateError('Existing Bubblewrap Lean profile requires x86-64')
        return 'linux', 'linux-x86_64'
    operating_system = {'win32': 'windows', 'linux': 'linux', 'darwin': 'darwin'}.get(sys.platform)
    if architecture not in ('x86_64', 'aarch64') or operating_system == 'windows' and architecture != 'x86_64':
        raise StateError('No supported official Lean distribution for this OS/architecture')
    marker = operating_system + ('_aarch64' if architecture == 'aarch64' else '')
    return marker, operating_system + '-' + architecture
