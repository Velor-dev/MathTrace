"""Build and verify an isolated runtime wheel without removing retained evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid
import zipfile
from package_runtime import build_wheel, validate_wheel

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / 'work' / 'validation' / 'packaging' / ('runtime-' + uuid.uuid4().hex)
    output.mkdir(parents=True)
    def run(arguments, *, cwd=ROOT):
        result = subprocess.run(arguments, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        log = {'arguments': arguments, 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
        (output / ('process-' + str(len(list(output.glob('process-*.json')))) + '.json')).write_text(json.dumps(log, indent=2), encoding='utf-8')
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout
    build_wheel(output)
    wheels = list(output.glob('*.whl'))
    if len(wheels) != 1:
        raise RuntimeError('Expected one exact runtime wheel')
    wheel = wheels[0]
    source = {name.removeprefix('mathtrace/'): content
              for name, content in validate_wheel(wheel).items()}
    installed = output / 'runtime'
    install = run([sys.executable, '-m', 'pip', 'install', '--no-deps', '--target', str(installed), str(wheel)])
    (output / 'install.log').write_text(install, encoding='utf-8')
    for name, content in source.items():
        if (installed / 'mathtrace' / name).read_bytes() != content:
            raise RuntimeError('Installed runtime differs: ' + name)
    code = "import sys; sys.path.insert(0,sys.argv[1]); from mathtrace.cli import main; main(['identity'])"
    identity = json.loads(run([sys.executable, '-I', '-c', code, str(installed)], cwd=output))
    if Path(identity['result']['module']).resolve() != (installed / 'mathtrace' / 'cli.py').resolve():
        raise RuntimeError('Isolated identity resolved a different runtime')
    evidence = {'wheel': str(wheel), 'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
        'runtime_files_exact': {p: True for p in source},
        'source_hashes': {p: hashlib.sha256(b).hexdigest() for p, b in source.items()},
        'isolated_installed_identity': identity,
        'scope': 'Runtime-only wheel; native installation and documentation use checkout tooling'}
    path = output / 'wheel-evidence.json'
    path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps({'evidence': str(path), 'wheel': str(wheel), 'sha256': evidence['wheel_sha256'],
                      'exact_runtime_files': len(source)}))


if __name__ == '__main__':
    main()
