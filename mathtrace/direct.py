"""Native recorder for reviewed local code. This is not a sandbox."""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mathtrace.store import StateError, digest
from mathtrace.backend import EXECUTION_PROTOCOL

OUTPUT_LIMIT = 4 * 1024 * 1024
COMPILED_FILES = ('Main.olean', 'Main.olean.server', 'Main.olean.private', 'Main.ir')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def environment(directory):
    keep = {'SYSTEMROOT', 'WINDIR', 'COMSPEC'} if os.name == 'nt' else set()
    env = {k: v for k, v in os.environ.items() if k.upper() in keep}
    env.update(HOME=str(directory), USERPROFILE=str(directory), TEMP=str(directory),
               TMP=str(directory), TMPDIR=str(directory), LANG='C.UTF-8',
               PATH=str(Path(sys.executable).parent))
    return env


class WindowsJob:
    """Process lifetime only; no filesystem, network or security isolation."""
    def __init__(self):
        import ctypes as c
        from ctypes import wintypes as w
        self.c, self.w = c, w
        self.k = c.WinDLL('kernel32', use_last_error=True)
        self.k.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
        self.k.CreateJobObjectW.restype = w.HANDLE
        self.k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.k.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
        self.k.QueryInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.c_void_p]
        self.k.CloseHandle.argtypes = [w.HANDLE]
        self.handle = self.k.CreateJobObjectW(None, None)
        if not self.handle:
            raise c.WinError(c.get_last_error())

    def assign(self, process):
        if not self.k.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise self.c.WinError(self.c.get_last_error())

    def close(self):
        if not self.handle:
            return
        c, w = self.c, self.w
        class Accounting(c.Structure):
            _fields_ = [('User', c.c_int64), ('Kernel', c.c_int64),
                        ('PeriodUser', c.c_int64), ('PeriodKernel', c.c_int64),
                        ('Faults', w.DWORD), ('Total', w.DWORD),
                        ('Active', w.DWORD), ('Terminated', w.DWORD)]
        if not self.k.TerminateJobObject(self.handle, 1):
            raise c.WinError(c.get_last_error())
        end = time.monotonic() + 10
        while True:
            info = Accounting()
            if not self.k.QueryInformationJobObject(self.handle, 1, c.byref(info), c.sizeof(info), None):
                raise c.WinError(c.get_last_error())
            if info.Active == 0:
                break
            if time.monotonic() >= end:
                raise RuntimeError('Native job teardown is uncertain')
            time.sleep(.01)
        self.k.CloseHandle(self.handle)
        self.handle = None


def run(command, directory, timeout, *, extra_environment=None, address_space_bytes=2 * 1024**3):
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 86400:
        raise StateError('Invalid native execution timeout')
    env = {**environment(directory), **(extra_environment or {})}
    limits = {'wall_seconds': timeout, 'captured_output_bytes': OUTPUT_LIMIT,
              'filesystem_bytes': 'not enforced', 'aggregate_memory_bytes': 'not enforced'}
    options = {}
    if os.name != 'nt':
        import resource
        limits.update(address_space_bytes=address_space_bytes if sys.platform == 'linux' else 'not enforced', file_bytes=128 * 1024**2,
                      process_scope='POSIX session/process group; escaped descendants not contained')
        def apply_limits():
            for key, value in ([(resource.RLIMIT_CORE, 0),
                                (resource.RLIMIT_FSIZE, 128 * 1024**2),
                                (resource.RLIMIT_CPU, math.ceil(timeout) + 1)]
                               + ([(resource.RLIMIT_AS, address_space_bytes)] if sys.platform == 'linux' else [])):
                resource.setrlimit(key, (value, value))
        options.update(start_new_session=True, preexec_fn=apply_limits)
        launched = command
        job = None
    else:
        limits.update(address_space_bytes='not enforced', process_scope='Windows Job Object')
        job = WindowsJob()
        # The trusted gate cannot start the workload before job assignment.
        gate = 'import subprocess,sys,json; token=sys.stdin.buffer.read(1); token==b"G" or sys.exit(125); args=json.loads(sys.argv[1]); sys.exit(subprocess.call(args,stdin=subprocess.DEVNULL))'
        launched = [sys.executable, '-I', '-c', gate, json.dumps(command)]
        options['creationflags'] = subprocess.CREATE_NO_WINDOW
    captured = {'stdout': bytearray(), 'stderr': bytearray()}
    lock, overflow = threading.Lock(), threading.Event()
    total = 0
    def drain(stream, key):
        nonlocal total
        try:
            while data := stream.read(65536):
                with lock:
                    room = max(0, OUTPUT_LIMIT - total)
                    captured[key].extend(data[:room])
                    total += min(room, len(data))
                    if len(data) > room:
                        overflow.set()
        finally:
            stream.close()
    process, threads = None, []
    started = time.monotonic()
    timed_out = False
    try:
        process = subprocess.Popen(launched, cwd=directory, env=env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, **options)
        if job:
            job.assign(process)
            process.stdin.write(b'G')
            process.stdin.flush()
        process.stdin.close()
        threads = [threading.Thread(target=drain, args=(process.stdout, 'stdout'), daemon=True),
                   threading.Thread(target=drain, args=(process.stderr, 'stderr'), daemon=True)]
        for thread in threads:
            thread.start()
        while process.poll() is None:
            if overflow.is_set() or time.monotonic() - started >= timeout:
                timed_out = not overflow.is_set()
                break
            time.sleep(.01)
    finally:
        if process:
            try:
                if job:
                    job.close()
                else:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                # Also stop the gate if assignment itself failed.
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=10)
            except (OSError, subprocess.SubprocessError) as exc:
                raise RuntimeError('Native process teardown is uncertain; no terminal certificate') from exc
            for thread in threads:
                thread.join(timeout=2)
            if any(thread.is_alive() for thread in threads):
                raise RuntimeError('Native output handles remain live; teardown is uncertain')
        elif job:
            job.close()
    return {'command': command, 'exit_code': None if timed_out else process.returncode,
            'stdout': captured['stdout'].decode('utf-8', 'replace'),
            'stderr': captured['stderr'].decode('utf-8', 'replace'),
            'timed_out': timed_out, 'output_limited': overflow.is_set(),
            'duration_seconds': time.monotonic() - started, 'namespace_setup': None,
            'isolation_established': False, 'resource_limits': limits,
            'execution_environment': {'backend': 'direct-native-v1', 'platform': sys.platform,
                'architecture': platform.machine(), 'interpreter_hash': sha(sys.executable),
                'recorder_hash': sha(__file__), 'executable_hash': sha(command[0])}}


def collect(path, limit=16 * 1024**2):
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return None
    if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in (path, *path.parents)):
        raise StateError('Redirected retained output')
    with path.open('rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit or info.st_nlink != 1:
            raise StateError('Retained output is not a bounded regular file')
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise StateError('Retained output exceeded bound')
    return {'encoding': 'base64', 'content': base64.b64encode(raw).decode('ascii'),
            'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw)}


def stage_tree(spec, destination):
    from mathtrace.evidence import library_manifest
    if library_manifest(spec['root'])['files'] != spec['files']:
        raise StateError('Input manifest changed before staging')
    shutil.copytree(spec['root'], destination, symlinks=False)
    if library_manifest(str(destination))['files'] != spec['files']:
        raise StateError('Staged bytes differ from committed input')
    return destination


def formal(request, stage):
    from mathtrace.formal import validate_resolution
    from mathtrace.resolution import normalized_resolution
    from mathtrace.sandbox_runtime import bind_resolution
    tc = stage_tree(request['toolchain'], stage / 'toolchain')
    libs = [stage_tree(lib, stage / f'library-{i}') for i, lib in enumerate(request['libraries'])]
    replay_root = stage / 'replay'
    replay_root.mkdir()
    roots = {'platform': 'windows' if os.name == 'nt' else sys.platform, 'stage': str(stage),
             'paths': {'/toolchain': str(tc), '/replay': str(replay_root),
                       **{f'/libraries/{i}': str(p) for i, p in enumerate(libs)}}}
    env = {'LEAN_SYSROOT': str(tc), 'LEAN_PATH': os.pathsep.join(map(str, libs)), 'LEAN_NUM_THREADS': '2'}
    lean = str(tc / request['toolchain']['executable'])
    source = stage / 'Main.lean'
    source.write_text(request['source'], encoding='utf-8')
    def execute(command, timeout=None, extra=None):
        return run(command, stage, request['timeout'] if timeout is None else timeout,
                   extra_environment={**env, **(extra or {})}, address_space_bytes=8 * 1024**3)
    version = execute([lean, '-j2', '--version'], min(30, request['timeout']))
    result = execute([lean, '-j2', '-o', str(replay_root / 'Main.olean'), str(source)])
    compiled, parts, file_set, semantic, replay, binding, resolved, error, collection_error = None, {}, None, None, None, None, None, None, None
    try:
        blobs = {name: collect(replay_root / name) for name in COMPILED_FILES}
        compiled = blobs['Main.olean']
        parts = {k: v for k, v in blobs.items() if k != 'Main.olean' and v is not None}
        file_set = {k: ({'sha256': v['sha256'], 'size': v['size']} if v else None) for k, v in blobs.items()}
        if sum(v['size'] for v in blobs.values() if v) > 64 * 1024**2:
            raise StateError('Compiled family exceeds aggregate bound')
    except (OSError, StateError) as exc:
        collection_error = str(exc)
    if compiled and result['exit_code'] == 0 and not result['timed_out'] and not result['output_limited']:
        verification = request.get('verification')
        if verification is None:
            checker = str(tc / 'bin' / ('leanchecker.exe' if os.name == 'nt' else 'leanchecker'))
            replay = execute([checker, '--fresh', 'Main'], extra={'LEAN_PATH': os.pathsep.join(map(str, [replay_root, *libs]))})
        else:
            helper = stage / 'Verifier.lean'
            helper.write_text(verification['helper_source'], encoding='utf-8')
            output = stage / 'MathTraceSemantics.json'
            replay = execute([lean, '-j2', '--run', str(helper), '--verify-retained-output',
                              str(output), 'Main', verification['check_symbol'], str(replay_root), *map(str, libs)],
                             extra={'LEAN_PATH': ''})
            binding = {'protocol': verification['protocol'], 'profile': verification['profile'],
                       'check_symbol': verification['check_symbol'],
                       'helper_sha256': hashlib.sha256(verification['helper_source'].encode()).hexdigest(),
                       'source_sha256': hashlib.sha256(request['source'].encode()).hexdigest(),
                       'compiled_file_set_hash': digest(file_set)}
            try:
                semantic = collect(output, 64 * 1024**2)
                if semantic and replay['exit_code'] == 0:
                    report = json.loads(base64.b64decode(semantic['content']))
                    # Reuse exact family/manifest validation after portable normalization.
                    virtual = {k: (Path(v), request['toolchain']['files'] if k == '/toolchain' else
                                   {n: b['sha256'] for n, b in file_set.items() if b} if k == '/replay' else
                                   request['libraries'][int(k.rsplit('/', 1)[1])]['files'])
                               for k, v in roots['paths'].items()}
                    provisional = {'reference': [], 'candidate': []}
                    norm, _ = normalized_resolution(report['resolution'], provisional, roots, len(libs))
                    resolved = bind_resolution(norm, virtual, [f'/libraries/{i}' for i in range(len(libs))])
                    resolved['channel'] = 'Lean resolution reconstructed under byte-verified staged roots and checked against staged bytes'
                    for key in ('reference_search_roots', 'candidate_search_roots'):
                        resolved[key] = report['resolution'][key]
                    validate_resolution(report['resolution'], resolved, request['toolchain'], request['libraries'], file_set, roots=roots)
            except (ValueError, TypeError, KeyError, OSError) as exc:
                error = str(exc)
    for spec, path in [(request['toolchain'], tc), *zip(request['libraries'], libs)]:
        from mathtrace.evidence import library_manifest
        if library_manifest(str(path))['files'] != spec['files']:
            error = 'Staged input bytes changed during checking'
    # Retained objects must still equal the exact compilation outputs.
    if file_set and any(collect(replay_root / n) != (compiled if n == 'Main.olean' else parts.get(n)) for n in COMPILED_FILES):
        error = 'Retained compilation bytes changed during verification'
    return {'version': version, 'result': result, 'replay': replay, 'compiled_output': compiled,
            'compiled_parts': parts, 'compiled_file_set': file_set, 'semantic_output': semantic,
            'verification_binding': binding, 'resolved_inputs': resolved, 'verification_error': error,
            'artifact_collection_error': collection_error, 'staged_roots': roots}


def atomic(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    if os.name != 'nt':
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def record(request):
    request = dict(request)
    journal = request.pop('_journal', None)
    if request.get('execution_protocol') != EXECUTION_PROTOCOL or request.get('execution_mode') != 'direct':
        raise StateError('Native recorder requires explicit mode-aware request')
    directory = None
    with tempfile.TemporaryDirectory(prefix='mathtrace-direct-') as temporary:
        stage = Path(temporary).resolve()
        producer = {'pid': os.getpid(), 'started_ns': time.time_ns(), 'nonce': uuid.uuid4().hex,
                    'recorder_hash': sha(__file__), 'execution_mode': 'direct',
                    'execution_protocol': EXECUTION_PROTOCOL, 'stage': str(stage)}
        if journal:
            if digest(request) != journal['request_hash']:
                raise StateError('Native request differs from committed intent')
            directory = Path(journal['directory']).resolve()
            directory.parent.mkdir(parents=True, exist_ok=True)
            directory.mkdir()
            producer.update(execution=journal['execution'], request_hash=journal['request_hash'])
            atomic(directory / 'started.json', producer)
        # Cleanup uncertainty must escape: no terminal certificate is published.
        try:
            if request.get('operation') == 'formal':
                result = formal(request, stage)
            else:
                source = stage / 'program.py'
                source.write_text(request['source'], encoding='utf-8')
                (stage / 'inputs.json').write_text(json.dumps(request.get('inputs', {}), allow_nan=False), encoding='utf-8')
                result = run([sys.executable, '-I', str(source)], stage, request['timeout'])
            envelope = {'ok': True, 'result': result}
        except RuntimeError:
            raise
        except Exception as exc:
            envelope = {'ok': False, 'error': str(exc)}
        envelope.update(execution_mode='direct', execution_protocol=EXECUTION_PROTOCOL,
                        producer=producer, producer_hash=digest(producer),
                        teardown='recorder-owned-processes-waited')
        if journal:
            envelope.update(execution=journal['execution'], request_hash=journal['request_hash'])
            atomic(directory / 'terminal.json', envelope)
        return envelope


def invoke(request, timeout, *, journal=None):
    payload = {**request, **({'_journal': journal} if journal else {})}
    try:
        observed = subprocess.run([sys.executable, '-I', str(Path(__file__).resolve())],
            input=json.dumps(payload, allow_nan=False), capture_output=True, text=True,
            encoding='utf-8', timeout=timeout, env=environment(Path(tempfile.gettempdir())))
        envelope = json.loads(observed.stdout)
    except (subprocess.SubprocessError, ValueError, OSError) as exc:
        raise StateError('Native recorder unavailable; termination is uncertain, do not retry') from exc
    if not envelope.get('ok'):
        raise StateError(envelope.get('error', observed.stderr))
    if journal and (envelope.get('execution') != journal['execution'] or envelope.get('request_hash') != journal['request_hash']):
        raise StateError('Native response does not bind exact attempt')
    return {**envelope['result'], **({'_producer': {k: v for k, v in envelope.items() if k != 'result'}} if journal else {})}


if __name__ == '__main__':
    try:
        print(json.dumps(record(json.load(sys.stdin)), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        sys.exit(2)
