"""Installer bridge to existing runtime operations; never qualifies mathematics."""
import json
import sys
from pathlib import Path
from mathtrace.store import Store, StateError
from mathtrace.toolchain import Toolchains, execution_target, verify_toolchain


def provision(project, version, mode, *, verify_only=False):
    database = Path(project) / '.math/state.sqlite'
    with Store(database, create=not database.exists() and not verify_only) as store:
        health = store.health()
        if not health['ok']:
            raise StateError('Existing campaign health failed')
        _, target = execution_target(mode)
        matching = [r for r in store.records('toolchain')
                    if r['data']['version'] == version and r['data']['platform'] == target]
        if matching:
            record = matching[-1]
            verify_toolchain(record)  # Do not replace a tampered recorded distribution.
            if store.status(record['id']) != 'installed':
                raise StateError('Matching toolchain is not installed')
            identifier = record['id']
        elif verify_only:
            raise StateError('No verified pinned toolchain in campaign')
        else:
            identifier = Toolchains(store).install_lean(version, execution_mode=mode)
        return {'toolchain': identifier, 'health': store.health(), 'target': target}


if __name__ == '__main__':
    result = provision(Path.cwd(), sys.argv[1], sys.argv[2], verify_only='--verify' in sys.argv[3:])
    print(json.dumps(result))
