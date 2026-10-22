"""Unpublished packed-installer acceptance with actual native Lean; no host sessions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_npm import assemble, validate_archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lean-archive', type=Path, help='Optional cached official ZIP, still verified against live publisher digest')
    args = parser.parse_args()
    output = ROOT / 'work/validation/npm' / ('acceptance-' + uuid.uuid4().hex)
    output.mkdir(parents=True)
    package = assemble(output / 'release')
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')

    def run(command, cwd, name):
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        (output / (name + '.json')).write_text(json.dumps({'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}, indent=2))
        if result.returncode:
            raise RuntimeError(f'{name} failed; see {output / (name + ".json")}')
        return result.stdout

    packed = json.loads(run([npm, 'pack', '--ignore-scripts', '--json', '--cache', str(output / 'npm-cache')], package, 'pack'))
    archive = package / packed[0]['filename']
    validate_archive(archive)
    extracted = output / 'unpacked'
    with tarfile.open(archive) as z:
        z.extractall(extracted, filter='data')
    deployed_package = extracted / 'package'
    project = output / 'independent project'
    project.mkdir()
    (project / 'AGENTS.md').write_bytes(b'Owner project instructions\r\n')
    if args.lean_archive:
        cached = project / '.math/toolchains/v4.30.0' / args.lean_archive.name
        cached.parent.mkdir(parents=True)
        shutil.copyfile(args.lean_archive, cached)
    install_args = ['node', str(deployed_package / 'bin/install.cjs'), '--harness', 'codex', '--python', sys.executable]
    installed = json.loads(run(install_args, project, 'install'))
    repeated = json.loads(run(install_args, project, 'repeat'))
    if repeated['changedFiles'] != 0:
        raise RuntimeError('Repeat installation changed files')
    hidden = extracted / 'package-unavailable'
    deployed_package.rename(hidden)
    identity = json.loads(run(['node', '.mathtrace/run.cjs', 'identity'], project, 'identity'))
    health = json.loads(run(['node', '.mathtrace/run.cjs', 'health'], project, 'health'))
    receipt = json.loads((project / '.mathtrace/install.json').read_text())
    python = project / receipt['runtime'] / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    code = '''import json
from mathtrace.store import Store
from mathtrace.toolchain import verify_toolchain
from mathtrace.backend import invoke, EXECUTION_PROTOCOL
with Store('.math/state.sqlite') as store:
 r=store.get(%r); verify_toolchain(r)
 request={'operation':'formal','source':'theorem installerSmoke : True := by trivial\\n#print axioms installerSmoke\\n','toolchain':r['data'],'libraries':[],'timeout':300,'execution_mode':'direct','execution_protocol':EXECUTION_PROTOCOL}
 result=invoke(request); verify_toolchain(r)
 checked=result['result']['exit_code']==0 and bool(result.get('compiled_output')) and 'sorryAx' not in result['result']['stdout']
 assert checked, result['result']
 print(json.dumps({'passed':checked,'stdout':result['result']['stdout'],'execution_mode':'direct','scope':'Actual pinned compiler smoke check; no independent assessment or mathematical release qualification'}))
''' % receipt['toolchain']
    smoke = json.loads(run([str(python), '-I', '-c', code], project, 'lean-smoke'))
    evidence = {'passed': installed['installed'] and health['result']['ok'] and smoke['passed'],
                'project': str(project), 'packed_archive': str(archive), 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'identity': identity, 'repeat_changes': repeated['changedFiles'], 'actual_lean': smoke,
                'harness': 'Real installed Codex CLI version preflight; no model/host session launched',
                'source_and_package_access': 'Installed operations executed outside source with package directory renamed'}
    (output / 'evidence.json').write_text(json.dumps(evidence, indent=2))
    print(json.dumps({'passed': evidence['passed'], 'evidence': str(output / 'evidence.json')}))


if __name__ == '__main__':
    main()
