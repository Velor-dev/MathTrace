"""Clean wheel assembly and complete archive checks, without touching old builds."""
import base64
import configparser
import csv
from email.parser import BytesParser
import hashlib
import io
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LEGAL_FILES = ('LICENSE',)
LICENSE_EXPRESSION = 'LicenseRef-MathTrace-Proprietary'


def source_files(root=ROOT):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in (root / 'mathtrace').iterdir()
            if p.is_file() and p.suffix in {'.py', '.lean'}}


def validate_wheel(wheel, root=ROOT):
    project = tomllib.loads((root / 'pyproject.toml').read_text())['project']
    version = project['version']
    info = f'mathtrace-{version}.dist-info/'
    expected = source_files(root)
    with zipfile.ZipFile(wheel) as z:
        names = z.namelist()
        allowed_meta = {info + n for n in ('METADATA', 'WHEEL', 'entry_points.txt', 'top_level.txt', 'RECORD')}
        notices = {info + 'licenses/' + name for name in LEGAL_FILES}
        allowed = set(expected) | allowed_meta | notices
        if len(names) != len(set(names)) or set(names) != allowed:
            raise ValueError('Unexpected, missing or duplicate wheel members: ' + str(set(names) ^ allowed))
        for member in z.infolist():
            name = member.filename
            parts = PurePosixPath(name)
            if (parts.is_absolute() or '..' in parts.parts or '\\' in name or ':' in name
                    or stat.S_ISLNK(member.external_attr >> 16)):
                raise ValueError('Unsafe wheel member: ' + name)
        for name, content in expected.items():
            if z.read(name) != content:
                raise ValueError('Runtime content differs: ' + name)
        for name in LEGAL_FILES:
            if z.read(info + 'licenses/' + name) != (root / name).read_bytes():
                raise ValueError('Legal file differs: ' + name)
        metadata = BytesParser().parsebytes(z.read(info + 'METADATA'))
        if (metadata['Name'] != project['name'] or metadata['Version'] != version
                or metadata['Requires-Python'] != project['requires-python'] or metadata.get_all('Requires-Dist')):
            raise ValueError('Unexpected package metadata or runtime dependencies')
        if (metadata['License-Expression'] != LICENSE_EXPRESSION
                or sorted(metadata.get_all('License-File', [])) != sorted(LEGAL_FILES)
                or metadata['Author'] != 'Velor-dev'):
            raise ValueError('Unexpected license or author metadata')
        entry = configparser.ConfigParser()
        entry.read_string(z.read(info + 'entry_points.txt').decode())
        if dict(entry['console_scripts']) != {'mathtrace': 'mathtrace.cli:main'}:
            raise ValueError('Unexpected entry points')
        if z.read(info + 'top_level.txt').decode().strip() != 'mathtrace':
            raise ValueError('Unexpected top-level packages')
        wheel_metadata = BytesParser().parsebytes(z.read(info + 'WHEEL'))
        if (wheel_metadata['Wheel-Version'] != '1.0' or wheel_metadata['Root-Is-Purelib'] != 'true'
                or wheel_metadata.get_all('Tag') != ['py3-none-any']):
            raise ValueError('Unexpected wheel format or platform metadata')
        record = list(csv.reader(io.StringIO(z.read(info + 'RECORD').decode())))
        if len(record) != len(names) or {row[0] for row in record} != set(names):
            raise ValueError('Invalid RECORD member set')
        for name, checksum, size in record:
            if name == info + 'RECORD':
                if checksum or size:
                    raise ValueError('Invalid RECORD self entry')
                continue
            content = z.read(name)
            digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b'=').decode()
            if checksum != 'sha256=' + digest or size != str(len(content)):
                raise ValueError('Invalid RECORD checksum: ' + name)
    return expected


def build_wheel(output, root=ROOT):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='wheel-source-', dir=output) as temp:
        stage = Path(temp)
        for name in ('pyproject.toml', *LEGAL_FILES):
            shutil.copy2(root / name, stage / name)
        for name, content in source_files(root).items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        result = subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--no-deps',
                                 str(stage), '--wheel-dir', str(output)], capture_output=True, text=True)
        (output / 'build.log').write_text(result.stdout + result.stderr, encoding='utf-8')
        if result.returncode:
            raise RuntimeError('Clean wheel build failed; see ' + str(output / 'build.log'))
    wheel = output / f'mathtrace-{tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]}-py3-none-any.whl'
    validate_wheel(wheel, root)
    return wheel
