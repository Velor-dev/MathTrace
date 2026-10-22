"""Two explicit execution modes; no host-policy or configuration routing."""
from __future__ import annotations

import sys
from .store import StateError

EXECUTION_PROTOCOL = 'mode-aware-execution-v1'


def mode(value=None):
    value = 'direct' if value is None else value
    if value not in ('direct', 'bubblewrap'):
        raise StateError('execution_mode must be direct or bubblewrap')
    if value == 'direct' and sys.platform not in ('win32', 'linux', 'darwin'):
        raise StateError('Direct execution is unsupported on this operating system')
    if value == 'bubblewrap' and sys.platform not in ('win32', 'linux'):
        raise StateError('Bubblewrap requires Linux or the existing Windows/Ubuntu WSL backend')
    return value


def invoke(request, *, journal=None):
    selected = mode(request['execution_mode'])
    if selected == 'bubblewrap':
        from .sandbox import invoke as transport
    else:
        from .direct import invoke as transport
    timeout = request['timeout'] * 3 + 600 if request.get('operation') == 'formal' else request['timeout'] + 30
    return transport(request, timeout, journal=journal)
