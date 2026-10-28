import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from mathtrace.store import Store, StateError
from mathtrace.toolchain import execution_target

spec = importlib.util.spec_from_file_location('installer_bootstrap', Path(__file__).resolve().parents[1] / 'npm/lib/bootstrap.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.version = 'v4.30.0'
        self.marker = execution_target()[0]
        self.name = f'lean-{self.version}-{self.marker}.zip'
        self.binary = 'lean.exe' if sys.platform == 'win32' else 'lean'
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr(f'lean/bin/{self.binary}', b'fixture only, never executed')
            z.writestr('lean/lib/lean/Init.olean', b'fixture library')
        self.archive = buf.getvalue()
        self.digest = hashlib.sha256(self.archive).hexdigest()

    def download(self, request, **kwargs):
        url = request.full_url if hasattr(request, 'full_url') else request
        if url.startswith('https://api.github.com'):
            return io.BytesIO(json.dumps({'assets': [{'name': self.name, 'digest': 'sha256:' + self.digest,
                'browser_download_url': f'https://github.com/leanprover/lean4/releases/download/{self.version}/{self.name}'}]}).encode())
        return io.BytesIO(self.archive)

    def test_initialize_reuse_and_retry_preserve_exact_events(self):
        with patch('mathtrace.toolchain.urllib.request.urlopen', side_effect=self.download):
            first = bootstrap.provision(self.root, self.version, 'direct')
        with Store(self.root / '.math/state.sqlite') as store:
            before = store.export()
        with patch('mathtrace.toolchain.urllib.request.urlopen', side_effect=AssertionError('must reuse')):
            second = bootstrap.provision(self.root, self.version, 'direct')
            verified = bootstrap.provision(self.root, self.version, 'direct', verify_only=True)
        self.assertEqual(first['toolchain'], second['toolchain'])
        self.assertEqual(verified['toolchain'], first['toolchain'])
        with Store(self.root / '.math/state.sqlite') as store:
            self.assertEqual(before, store.export())
            toolchain = store.get(first['toolchain'])
        (Path(toolchain['data']['root']) / 'extra').write_bytes(b'tamper')
        with self.assertRaisesRegex(StateError, 'file set'):
            bootstrap.provision(self.root, self.version, 'direct')

    def test_failed_download_keeps_valid_empty_campaign(self):
        with patch('mathtrace.toolchain.urllib.request.urlopen', side_effect=OSError('download failed')):
            with self.assertRaises(OSError):
                bootstrap.provision(self.root, self.version, 'direct')
        with Store(self.root / '.math/state.sqlite') as store:
            self.assertTrue(store.health()['ok'])
            self.assertEqual(store.records(), [])
        with patch('mathtrace.toolchain.urllib.request.urlopen', side_effect=self.download):
            self.assertTrue(bootstrap.provision(self.root, self.version, 'direct')['health']['ok'])

    def test_existing_corrupt_database_is_not_replaced(self):
        database = self.root / '.math/state.sqlite'; database.parent.mkdir(); database.write_bytes(b'owner corrupted data')
        with self.assertRaises(Exception):
            bootstrap.provision(self.root, self.version, 'direct')
        self.assertEqual(database.read_bytes(), b'owner corrupted data')

    def test_invalid_publisher_digest_never_creates_toolchain_record(self):
        self.digest = '0' * 64
        with patch('mathtrace.toolchain.urllib.request.urlopen', side_effect=self.download):
            with self.assertRaisesRegex(StateError, 'digest mismatch'):
                bootstrap.provision(self.root, self.version, 'direct')
        with Store(self.root / '.math/state.sqlite') as store:
            self.assertEqual(store.records('toolchain'), [])


    def test_fresh_provision_does_not_call_verify_toolchain_redundantly(self):
        with patch.object(bootstrap, 'verify_toolchain', wraps=bootstrap.verify_toolchain) as mock_verify, \
             patch('mathtrace.toolchain.urllib.request.urlopen', side_effect=self.download):
            first = bootstrap.provision(self.root, self.version, 'direct')
            mock_verify.assert_not_called()
            second = bootstrap.provision(self.root, self.version, 'direct')
            self.assertEqual(mock_verify.call_count, 1)
            verified = bootstrap.provision(self.root, self.version, 'direct', verify_only=True)
            self.assertEqual(mock_verify.call_count, 2)
            self.assertEqual(first['toolchain'], second['toolchain'])
            self.assertEqual(verified['toolchain'], first['toolchain'])
