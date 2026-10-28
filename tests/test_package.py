"""Release archives must reject even correctly checksummed stale packages."""
import shutil
import tempfile
from pathlib import Path
import unittest
import zipfile
import warnings
from tools.package_runtime import ROOT, LEGAL_FILES, build_wheel, validate_wheel
from mathtrace import __version__


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name) / 'dirty'
        cls.root.mkdir()
        for name in ('pyproject.toml', *LEGAL_FILES):
            shutil.copy2(ROOT / name, cls.root / name)
        shutil.copytree(ROOT / 'mathtrace', cls.root / 'mathtrace', ignore=shutil.ignore_patterns('__pycache__'))
        stale = cls.root / 'build/lib/gsd_math/__init__.py'
        stale.parent.mkdir(parents=True)
        stale.write_text('legacy')
        cls.wheel = build_wheel(Path(cls.temp.name) / 'output', cls.root)

    def test_dirty_build_is_clean_and_keeps_original(self):
        validate_wheel(self.wheel, self.root)
        self.assertTrue((self.root / 'build/lib/gsd_math/__init__.py').is_file())
        with zipfile.ZipFile(self.wheel) as z:
            self.assertFalse(any(n.startswith('gsd_math/') for n in z.namelist()))

    def test_legal_files_and_metadata_rejected_with_valid_checksums(self):
        import base64
        import csv
        import hashlib
        import io
        with zipfile.ZipFile(self.wheel) as z:
            original = {n: z.read(n) for n in z.namelist()}
        info = f'mathtrace-{__version__}.dist-info/'
        mutations = []
        for name in LEGAL_FILES:
            member = info + 'licenses/' + name
            mutations.extend([(member, None), (member, b'changed legal terms')])
        metadata = original[info + 'METADATA']
        for old, new in [(b'LicenseRef-MathTrace-Proprietary', b'MIT'),
                         (b'Velor-dev', b'Other'),
                         (b'License-File: LICENSE', b'License-File: other')]:
            self.assertIn(old, metadata)
            mutations.append((info + 'METADATA', metadata.replace(old, new)))
        for member, content in mutations:
            with self.subTest(member=member, content=content):
                files = dict(original)
                if content is None:
                    del files[member]
                else:
                    files[member] = content
                record_name = info + 'RECORD'
                record = io.StringIO(newline='')
                writer = csv.writer(record)
                for name, data in files.items():
                    if name != record_name:
                        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
                        writer.writerow([name, 'sha256=' + digest, len(data)])
                writer.writerow([record_name, '', ''])
                files[record_name] = record.getvalue().encode()
                path = Path(self.temp.name) / 'legal-bad.whl'
                with zipfile.ZipFile(path, 'w') as z:
                    for name, data in files.items():
                        z.writestr(name, data)
                with self.assertRaises(ValueError):
                    validate_wheel(path, self.root)

    def test_contaminated_archives_are_rejected(self):
        with zipfile.ZipFile(self.wheel) as z:
            original = {n: z.read(n) for n in z.namelist()}
        for name, content in [('gsd_math/__init__.py', b'legacy'), ('extra.txt', b'extra'),
                              ('../escape', b'escape'), ('mathtrace/cli.py', b'changed'),
                              (f'mathtrace-{__version__}.dist-info/METADATA', b'Name: other\nVersion: 9\n')]:
            with self.subTest(member=name):
                path = Path(self.temp.name) / 'bad.whl'
                with zipfile.ZipFile(path, 'w') as z:
                    for n, b in (original | {name: content}).items():
                        z.writestr(n, b)
                with self.assertRaises(ValueError):
                    validate_wheel(path, self.root)
        with zipfile.ZipFile(path, 'w') as z, warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for n, b in original.items():
                z.writestr(n, b)
            z.writestr('mathtrace/cli.py', original['mathtrace/cli.py'])
        with self.assertRaises(ValueError):
            validate_wheel(path, self.root)
