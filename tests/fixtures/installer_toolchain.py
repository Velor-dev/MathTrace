"""Installer test only: synthetic publisher response, never executable Lean evidence."""
import hashlib
import importlib.util
import io
import json
import sys
from unittest.mock import patch
import zipfile
from pathlib import Path
from mathtrace.toolchain import execution_target

helper, version, mode = sys.argv[1:4]
marker = execution_target(mode)[0]
name = f'lean-{version}-{marker}.zip'
buffer = io.BytesIO()
with zipfile.ZipFile(buffer, 'w') as z:
    z.writestr('fixture/bin/' + ('lean.exe' if sys.platform == 'win32' else 'lean'), b'fixture only; never executed')
    z.writestr('fixture/lib/lean/Init.olean', b'fixture only')
archive = buffer.getvalue()


def download(request, **kwargs):
    url = request.full_url if hasattr(request, 'full_url') else request
    if url.startswith('https://api.github.com'):
        return io.BytesIO(json.dumps({'assets': [{'name': name, 'digest': 'sha256:' + hashlib.sha256(archive).hexdigest(),
            'browser_download_url': f'https://github.com/leanprover/lean4/releases/download/{version}/{name}'}]}).encode())
    return io.BytesIO(archive)


spec = importlib.util.spec_from_file_location('bootstrap', helper)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
with patch('mathtrace.toolchain.urllib.request.urlopen', side_effect=download):
    print(json.dumps(module.provision(Path.cwd(), version, mode, verify_only='--verify' in sys.argv[4:])))
