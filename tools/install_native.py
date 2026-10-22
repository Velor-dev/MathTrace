"""Replace only this project's managed .agents projection, preserving a verified archive."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mathtrace.native import runtime_files


def is_preserved_external(path: str) -> bool:
    return (
        path.startswith('skills/openspec-')
        or path.startswith('workflows/')
        or path == 'skills/.openspec-target'
    )


def install(root: Path):
    root = root.resolve()
    target = root / '.agents'
    if target.resolve() != target or target.parent != root:
        raise ValueError('Refusing to replace redirected or external .agents directory')
    if target.exists():
        for item in target.rglob('*'):
            if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
                raise ValueError('Redirected descendant in managed .agents projection')
    current = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in target.rglob('*') if p.is_file()} if target.exists() else {}
    current_math = {p: h for p, h in current.items() if not is_preserved_external(p)}
    current_external = {p: h for p, h in current.items() if is_preserved_external(p)}

    own_manifest = target / 'math-runtime-manifest.json'
    receipt_path = root / 'work/native-install.json'
    legacy_receipt = root / '.planning/native-install.json'
    if not receipt_path.is_file() and legacy_receipt.is_file():
        receipt_path = legacy_receipt

    if own_manifest.is_file():
        expected = json.loads(own_manifest.read_text(encoding='utf-8'))['files']
        manifest_hash = hashlib.sha256(own_manifest.read_bytes()).hexdigest()
        if receipt_path.is_file():
            receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
            if receipt['manifest_hash'] != manifest_hash:
                raise ValueError('Installed ownership manifest changed; reconcile against the previous installation receipt')
        else:
            # Bootstrap an earlier owned projection only if its manifest exactly
            # matches the current authoritative renderer; never trust added keys.
            generated = {p: hashlib.sha256(t.encode('utf-8')).hexdigest() for p, t in runtime_files().items()}
            if expected != generated:
                raise ValueError('No independent installation receipt for this manifest')
        unknown = set(current_math) - set(expected) - {'math-runtime-manifest.json'}
        changed = [p for p, h in expected.items() if current_math.get(p) != h]
    elif current_math:
        raise ValueError('Existing unmanaged .agents cannot be replaced by the owned math installer')
    else:
        unknown, changed, expected = set(), [], {}

    expected_directories = {p.as_posix() for name in expected for p in Path(name).parents if p.as_posix() != '.'}
    actual_directories = {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_dir()} if target.exists() else set()
    actual_math_dirs = {d for d in actual_directories if not is_preserved_external(d) and d not in {'workflows', 'skills'}}
    unknown |= {p + '/' for p in actual_math_dirs - expected_directories}
    if unknown or changed:
        raise ValueError(f'Unreconciled local changes: unknown={sorted(unknown)}, changed={changed}')

    archive = None
    if current:
        archive = root / 'work/archives' / f'agents-before-math-{uuid.uuid4().hex}.zip'
        if not archive.resolve().is_relative_to(root):
            raise ValueError('Archive location escapes the workspace')
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive_created = False
        try:
            with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as saved:
                archive_created = True
                for name in sorted(current):
                    saved.write(target / name, name)
            with zipfile.ZipFile(archive) as saved:
                if saved.testzip() is not None or set(saved.namelist()) != set(current):
                    raise ValueError('Archive verification failed')
                for name, hashed in current.items():
                    if hashlib.sha256(saved.read(name)).hexdigest() != hashed:
                        raise ValueError('Archived bytes differ; refusing replacement')
        except BaseException:
            if archive_created and archive.resolve().is_relative_to(root):
                archive.unlink(missing_ok=True)
            raise

    files = runtime_files()
    staged = root / 'work' / f'native-stage-{uuid.uuid4().hex}'
    if not staged.resolve().is_relative_to(root):
        raise ValueError('Staging location escapes the workspace')
    for name, text in files.items():
        destination = staged / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding='utf-8', newline='\n')
    for ext_path in current_external:
        dest = staged / ext_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target / ext_path, dest)

    manifest = {'name': 'mathtrace', 'files': {
        name: hashlib.sha256((staged / name).read_bytes()).hexdigest() for name in files}}
    (staged / 'math-runtime-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    # Verified absolute paths remain strictly within this root. The archive has
    # been checked before removing any installed file; no cross-shell deletion.
    try:
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(staged), str(target))
    except BaseException:
        if archive is not None:
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive) as saved:
                for name in current:
                    destination = (target / name).resolve()
                    if not destination.is_relative_to(target):
                        raise ValueError('Archive restore escaped target')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(saved.read(name))
        if staged.exists() and staged.resolve().is_relative_to(root):
            shutil.rmtree(staged)
        raise
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps({'manifest_hash': hashlib.sha256((target / 'math-runtime-manifest.json').read_bytes()).hexdigest(),
                                      'files': manifest['files'], 'previous_archive': str(archive) if archive else None}, indent=2), encoding='utf-8')
    return {'installed_files': len(files) + 1, 'archive': str(archive) if archive else None,
            'agents': len([name for name in files if name.startswith('agents/')]),
            'skills': len([name for name in files if name.startswith('skills/')])}


if __name__ == '__main__':
    print(json.dumps(install(ROOT), indent=2))
