"""Root-owned isolated computation transport; never silently execute on host."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys

from .store import StateError


def compute(source: str, inputs: dict, timeout: float, *, journal: dict | None = None) -> dict:
    if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 86400:
        raise StateError('Specify a finite positive execution timeout of at most one day')
    result = invoke({'source': source, 'inputs': inputs, 'timeout': timeout}, timeout + 20, journal=journal)
    if not result.get('namespace_setup') and not result['timed_out']:
        raise StateError('Sandbox namespace setup did not complete: ' + result['stderr'])
    return result


def check_lean(source: str, toolchain: dict, libraries: list[dict], timeout: float, *, journal: dict | None = None,
               verification: dict | None = None) -> dict:
    if toolchain.get('executable') != 'bin/lean':
        raise StateError('Formal isolation requires a provisioned Linux Lean toolchain')
    if not math.isfinite(timeout) or not 0 < timeout <= 86400:
        raise StateError('Invalid formal execution timeout')
    request = {'operation': 'formal', 'source': source, 'toolchain': toolchain,
               'libraries': libraries, 'timeout': timeout}
    if verification is not None:
        request['verification'] = verification
    return invoke(request, timeout * 2 + 600, journal=journal)


def invoke(request: dict, timeout: float, *, journal: dict | None = None) -> dict:
    if journal is not None:
        request = {**request, '_journal': journal}
    recorder = Path(__file__).with_name('sandbox_runtime.py').resolve()
    environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}
    if os.name == 'nt':
        environment = {key: value for key, value in os.environ.items()
                       if key.upper() in {'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'USERPROFILE', 'LOCALAPPDATA'}}
        prefix = [str(Path(os.environ['SystemRoot']) / 'System32/wsl.exe'), '-d', 'Ubuntu', '--exec']
        try:
            converted = subprocess.run(prefix + ['/usr/bin/wslpath', '-a', str(recorder)], env=environment,
                                       capture_output=True, text=True, timeout=15, check=True)
        except (subprocess.SubprocessError, OSError) as error:
            raise StateError('Ubuntu WSL execution environment is unavailable; no host fallback exists') from error
        command = prefix + ['/usr/bin/python3', '-I', converted.stdout.strip()]
    elif sys.platform == 'linux':
        command = ['/usr/bin/python3', '-I', str(recorder)]
    else:
        raise StateError('No verified isolated computation backend for this operating system')
    try:
        observed = subprocess.run(command, input=json.dumps(request, allow_nan=False),
                                  capture_output=True, text=True, encoding='utf-8', timeout=timeout, env=environment)
    except subprocess.TimeoutExpired as error:
        raise StateError('Sandbox recorder unavailable; execution status is uncertain, do not automatically retry') from error
    try:
        envelope = json.loads(observed.stdout)
    except ValueError as error:
        raise StateError('No valid sandbox recorder response; do not substitute an unsandboxed run') from error
    if observed.returncode or not envelope.get('ok'):
        raise StateError('Sandbox setup failed: ' + envelope.get('error', observed.stderr))
    if journal is not None and (envelope.get('execution') != journal['execution']
            or envelope.get('request_hash') != journal['request_hash']
            or envelope.get('teardown') != 'recorder-owned-processes-waited'):
        raise StateError('Sandbox response does not establish this exact attempt and teardown')
    result = envelope['result']
    if journal is not None:
        result = {**result, '_producer': {k: v for k, v in envelope.items() if k != 'result'}}
    return result
