"""Assemble and validate the npm artifact; never publish or alter source projections."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid
import tarfile
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.package_runtime import LEGAL_FILES, build_wheel, validate_wheel
from mathtrace import __version__
from mathtrace.native import runtime_files


def validate_archive(archive):
    with tarfile.open(archive) as z:
        members = z.getmembers()
        if any(not m.isfile() or not m.name.startswith('package/') or '..' in Path(m.name).parts or '\\' in m.name for m in members):
            raise ValueError('Unsafe npm archive entry')
        names = [m.name.removeprefix('package/') for m in members]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate npm archive entry')
        manifest = json.load(z.extractfile('package/payload/manifest.json'))
        if set(names) != set(manifest['files']) | {'payload/manifest.json'}:
            raise ValueError('Unexpected npm archive contents')
        for name, digest in manifest['files'].items():
            if hashlib.sha256(z.extractfile('package/' + name).read()).hexdigest() != digest:
                raise ValueError('npm archive hash differs: ' + name)
        metadata = json.load(z.extractfile('package/package.json'))
        if metadata['version'] != manifest['version'] or metadata.get('dependencies') or metadata.get('private') is not False:
            raise ValueError('npm metadata violates release contract')
        if (metadata.get('license') != 'SEE LICENSE IN LICENSE'
                or metadata.get('author') != 'Velor-dev'
                or metadata.get('scripts', {}).get('prepublishOnly') != json.loads(
                    (ROOT / 'npm/package.json').read_text())['scripts']['prepublishOnly']):
            raise ValueError('npm licensing or publication safeguards differ')
        for name in LEGAL_FILES:
            for prefix in ('package/', 'package/payload/'):
                if prefix + name not in z.getnames() or z.extractfile(prefix + name).read() != (ROOT / name).read_bytes():
                    raise ValueError('npm legal file differs: ' + prefix + name)
        # Check the nested wheel against maintained sources, not just its hash.
        with tempfile.TemporaryDirectory() as temporary:
            wheel = Path(temporary) / Path(manifest['wheel']).name
            wheel.write_bytes(z.extractfile('package/' + manifest['wheel']).read())
            validate_wheel(wheel)
    return manifest


def assemble(output):
    if tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['version'] != __version__:
        raise ValueError('Python distribution and runtime versions differ')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    package = output / 'package'
    shutil.copytree(ROOT / 'npm', package, ignore=shutil.ignore_patterns('test', 'payload', 'node_modules', '__pycache__', '*.pyc', '*.pyo', '*.tgz'))
    # npm normalizes executable shebang files during installation. Hash those
    # canonical LF bytes so installed bin files retain their manifest identity.
    executable = package / 'bin/install.cjs'
    executable.write_bytes(executable.read_bytes().replace(b'\r\n', b'\n'))
    for name in LEGAL_FILES:
        shutil.copy2(ROOT / name, package / name)
    wheel = build_wheel(output / 'wheel')
    validate_wheel(wheel)
    data = package / 'payload'
    data.mkdir()
    shutil.copy2(wheel, data / wheel.name)
    research = json.loads((ROOT / 'coding-harnesses/research.json').read_text(encoding='utf-8'))
    source = ROOT / 'coding-harnesses'
    # Copy only runtime guidance, never development plans or provenance snapshots.
    for relative in ['shared', *[h['id'] for h in research['harnesses']]]:
        target = data / 'coding-harnesses' / relative
        shutil.copytree(source / relative, target, ignore=shutil.ignore_patterns('__pycache__', '.kimi'))
    for name in ('README.md', 'catalog.json', 'research.json'):
        target = data / 'coding-harnesses' / name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(source / name, target)
    # The fresh native projection comes from the same runtime version as the wheel.
    native = data / 'coding-harnesses/antigravity/.agents'
    shutil.rmtree(native)
    for name, text in runtime_files().items():
        p = native / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8', newline='\n')
    docs = data / 'docs'
    docs.mkdir()
    for p in (ROOT / 'docs').glob('*.md'):
        if p.name not in ('README.md', 'installation.md'):
            shutil.copy2(p, docs / p.name)
    for name in LEGAL_FILES:
        shutil.copy2(ROOT / name, data / name)
    meta = json.loads((package / 'package.json').read_text())
    if meta['version'] != __version__:
        raise ValueError('npm and runtime versions differ')
    files = {p.relative_to(package).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in package.rglob('*') if p.is_file()}
    manifest = {'version': __version__, 'lean': 'v4.30.0', 'wheel': 'payload/' + wheel.name,
                'harnesses': research['harnesses'], 'files': files}
    (data / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return package


if __name__ == '__main__':
    destination = ROOT / 'work/validation/npm' / ('release-' + uuid.uuid4().hex)
    print(json.dumps({'package': str(assemble(destination))}))
