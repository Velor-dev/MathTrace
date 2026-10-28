"""Archive provenance tests; fixtures are never executed as Lean binaries."""

import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from mathtrace.store import Store, StateError
from mathtrace.toolchain import Toolchains, verify_toolchain, extract_distribution, execution_target, DownloadProgress


class ToolchainInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / 'state.sqlite', create=True)
        self.version = 'v4.99.0'
        marker = execution_target()[0]
        self.name = f'lean-{self.version}-{marker}.zip'
        self.prefix = f'lean-{self.version}-{marker}'
        self.binary = 'lean.exe' if sys.platform == 'win32' else 'lean'
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr(f'{self.prefix}/bin/{self.binary}', b'fixture binary: not executed')
            archive.writestr(f'{self.prefix}/lib/lean/Init.olean', b'fixture library bytes')
        self.archive = data.getvalue()
        self.hashed = hashlib.sha256(self.archive).hexdigest()

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def download_fixture(self, request, **kwargs):
        url = request.full_url if hasattr(request, 'full_url') else request
        if url.startswith('https://api.github.com/'):
            return io.BytesIO(json.dumps({'assets': [{'name': self.name,
                'digest': 'sha256:' + self.hashed,
                'browser_download_url': f'https://github.com/leanprover/lean4/releases/download/{self.version}/{self.name}'}]}).encode())
        res = io.BytesIO(self.archive)
        res.headers = {'Content-Length': str(len(self.archive))}
        return res

    def test_install_never_admits_preexisting_unpublished_files(self):
        old = self.root / 'toolchains' / self.version / 'distribution' / self.prefix / 'lib/lean/Injected.olean'
        old.parent.mkdir(parents=True)
        old.write_bytes(b'not in the verified publisher archive')
        with patch('mathtrace.toolchain.urllib.request.urlopen', side_effect=self.download_fixture):
            identifier = Toolchains(self.store).install_lean(self.version)
        record = self.store.get(identifier)
        self.assertEqual(set(record['data']['files']), {f'bin/{self.binary}', 'lib/lean/Init.olean'})
        self.assertNotEqual(Path(record['data']['root']), old.parents[2])
        self.assertTrue(old.is_file())  # No unrelated/pre-existing tree was deleted.
        self.assertFalse((Path(record['data']['root']) / 'lib/lean/Injected.olean').exists())
        verify_toolchain(record)
        injected = Path(record['data']['root']) / 'lib/lean/New.olean'
        injected.write_bytes(b'added after publication')
        with self.assertRaisesRegex(StateError, 'file set changed'):
            verify_toolchain(record)

    def test_failed_publication_leaves_no_partly_installed_tree_or_record(self):
        with patch('mathtrace.toolchain.urllib.request.urlopen', side_effect=self.download_fixture), \
             patch('mathtrace.toolchain.Path.rename', side_effect=OSError('publication failed')):
            with self.assertRaises(OSError):
                Toolchains(self.store).install_lean(self.version)
        directory = self.root / 'toolchains' / self.version
        self.assertEqual(list(directory.glob('.lean-stage-*')), [])
        self.assertEqual(list(directory.glob('distribution-*')), [])
        self.assertEqual(self.store.records('toolchain'), [])

    def test_safe_extraction_rejects_archive_path_escape(self):
        archive = self.root / 'bad.zip'
        with zipfile.ZipFile(archive, 'w') as package:
            package.writestr('../outside.olean', b'escape')
        with self.assertRaisesRegex(StateError, 'Unsafe path'):
            extract_distribution(archive, self.root, hashlib.sha256(archive.read_bytes()).hexdigest())
        self.assertFalse((self.root.parent / 'outside.olean').exists())
        self.assertEqual(list(self.root.glob('.lean-stage-*')), [])

    def test_missing_publisher_digest_is_rejected(self):
        metadata = {'assets':[{'name':self.name,'digest':None,
                    'browser_download_url':f'https://github.com/leanprover/lean4/releases/download/{self.version}/{self.name}'}]}
        with patch('mathtrace.toolchain.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(metadata).encode())):
            with self.assertRaisesRegex((StateError,TypeError),'digest|str|bytes'):
                Toolchains(self.store).install_lean(self.version)
        self.assertEqual(self.store.records('toolchain'),[])

    @unittest.skipIf(sys.platform == 'win32','Unix executable permission validation')
    def test_native_unix_executables_are_ready_after_extraction(self):
        archive = self.root/'native.zip'
        with zipfile.ZipFile(archive,'w') as package:
            package.writestr('lean/bin/lean',b'not executed')
            package.writestr('lean/bin/leanchecker',b'not executed')
        root,_,_ = extract_distribution(archive,self.root,hashlib.sha256(archive.read_bytes()).hexdigest(),target_platform='linux')
        self.assertTrue((root/'bin/lean').stat().st_mode & 0o111)
        self.assertTrue((root/'bin/leanchecker').stat().st_mode & 0o111)

    def test_download_progress_tty_rendering(self):
        buf = io.StringIO()
        buf.isatty = lambda: True
        progress = DownloadProgress(total_bytes=1000, stream=buf, label='TestTool')
        progress.update(250, force=True)
        progress.update(500, force=True)
        progress.finish()
        output = buf.getvalue()
        self.assertIn('TestTool', output)
        self.assertIn('%', output)
        self.assertTrue(output.endswith('\n'))

    def test_download_progress_non_tty_rendering(self):
        buf = io.StringIO()
        buf.isatty = lambda: False
        progress = DownloadProgress(total_bytes=1000, stream=buf, label='TestTool')
        progress.update(500, force=True)
        progress.finish()
        output = buf.getvalue()
        self.assertIn('Downloading TestTool: 50%', output)
        self.assertIn('Downloaded TestTool', output)

    def test_download_progress_indeterminate(self):
        buf = io.StringIO()
        buf.isatty = lambda: True
        progress = DownloadProgress(total_bytes=None, stream=buf, label='TestTool')
        progress.update(1024 * 1024, force=True)
        progress.finish()
        output = buf.getvalue()
        self.assertIn('1.0 MB', output)

    def test_extract_distribution_emits_status_messages(self):
        buf = io.StringIO()
        archive = self.root / 'extract_test.zip'
        archive.write_bytes(self.archive)
        marker = execution_target()[0]
        root, files, _ = extract_distribution(archive, self.root, self.hashed, target_platform=marker, stream=buf)
        output = buf.getvalue()
        self.assertIn('-> Extracting Lean distribution (2 files)...', output)
        self.assertIn('-> Verifying toolchain integrity against archive manifest...', output)
        self.assertIn('Verified toolchain integrity', output)

    def test_install_lean_emits_download_and_extraction_status(self):
        buf = io.StringIO()
        with patch('mathtrace.toolchain.urllib.request.urlopen', side_effect=self.download_fixture):
            identifier = Toolchains(self.store).install_lean(self.version, stream=buf)
        output = buf.getvalue()
        self.assertIn(f'Downloaded Lean {self.version}', output)
        self.assertIn('-> Extracting Lean distribution', output)
        self.assertIn('-> Verifying toolchain integrity against archive manifest...', output)
        self.assertIn('Verified toolchain integrity', output)
        record = self.store.get(identifier)
        self.assertEqual(self.store.status(identifier), 'installed')
