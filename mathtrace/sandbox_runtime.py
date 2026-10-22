"""Trusted Linux-side recorder. Executed by sandbox.py, never inside the job.

Only JSON source/inputs cross the boundary. No campaign paths are mounted.
Linux namespaces and bubblewrap are trusted; kernel exploits are outside scope.
"""
from __future__ import annotations

import hashlib
import base64
import array
import ctypes
import json
import math
import os
from pathlib import Path
import platform
try:
    import resource
except ImportError:
    resource = None
import selectors
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time


OUTPUT_LIMIT = 4 * 1024 * 1024
PACKAGE_VERSION = '0.9.0-1ubuntu0.1'
LIVE_PROCESSES = set()
COMPILED_FILES = ('Main.olean', 'Main.olean.server', 'Main.olean.private', 'Main.ir')
SEMANTIC_FILE = 'MathTraceSemantics.json'


class scmp_arg_cmp(ctypes.Structure):
    _fields_ = [
        ('arg', ctypes.c_uint),
        ('op', ctypes.c_uint),
        ('datum_a', ctypes.c_uint64),
        ('datum_b', ctypes.c_uint64),
    ]


def seccomp_filter():
    """Deny inherited kernel keyring access and AF_VSOCK socket communication."""
    library = ctypes.CDLL('libseccomp.so.2')
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    library.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint, ctypes.POINTER(scmp_arg_cmp)]
    library.seccomp_rule_add_array.restype = ctypes.c_int
    library.seccomp_export_bpf.argtypes = [ctypes.c_void_p, ctypes.c_int]
    library.seccomp_export_bpf.restype = ctypes.c_int
    library.seccomp_release.argtypes = [ctypes.c_void_p]
    library.seccomp_release.restype = None
    context = library.seccomp_init(0x7fff0000)  # SCMP_ACT_ALLOW
    if not context:
        raise RuntimeError('Cannot initialize required seccomp isolation filter')
    output = tempfile.TemporaryFile()
    try:
        for name in (b'keyctl', b'add_key', b'request_key'):
            number = library.seccomp_syscall_resolve_name(name)
            if number < 0 or library.seccomp_rule_add_array(context, 0x00050001, number, 0, None) != 0:  # ERRNO(EPERM)
                raise RuntimeError('Cannot install required keyring denial')
        for name in (b'io_uring_setup', b'io_uring_enter', b'io_uring_register'):
            number = library.seccomp_syscall_resolve_name(name)
            if number < 0 or library.seccomp_rule_add_array(context, 0x00050001, number, 0, None) != 0:  # ERRNO(EPERM)
                raise RuntimeError(f'Cannot install required io_uring denial for {name.decode()}')
        socket_nr = library.seccomp_syscall_resolve_name(b'socket')
        if socket_nr < 0:
            raise RuntimeError('Cannot resolve required socket syscall for AF_VSOCK denial')
        af_vsock = getattr(socket, 'AF_VSOCK', 40)
        vsock_cmp = (scmp_arg_cmp * 1)(scmp_arg_cmp(0, 4, af_vsock, 0))  # SCMP_CMP_EQ = 4
        if library.seccomp_rule_add_array(context, 0x00050001, socket_nr, 1, vsock_cmp) != 0:
            raise RuntimeError('Cannot install required AF_VSOCK socket denial')
        if library.seccomp_export_bpf(context, output.fileno()) != 0:
            raise RuntimeError('Cannot export seccomp isolation filter')
        output.seek(0)
        return output
    except BaseException:
        output.close()
        raise
    finally:
        library.seccomp_release(context)


keyring_filter = seccomp_filter


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def bubblewrap():
    local = Path.home() / '.local/share/mathtrace/bubblewrap/0.9.0-1ubuntu0.1/bwrap'
    if not local.is_file():
        fallback = Path.home() / '.local/share/gsd-math/bubblewrap/0.9.0-1ubuntu0.1/bwrap'
        if fallback.is_file():
            local = fallback
    if local.is_file():
        provenance = json.loads(local.with_name('provenance.json').read_text(encoding='utf-8'))
        if provenance.get('package') != 'bubblewrap=' + PACKAGE_VERSION or sha(local) != provenance.get('binary_sha256'):
            raise RuntimeError('Local bubblewrap differs from its provisioned package receipt')
        return str(local)
    installed = Path('/usr/bin/bwrap')
    if installed.is_file():
        metadata = installed.stat()
        if metadata.st_uid != 0 or metadata.st_mode & 0o022:
            raise RuntimeError('System bubblewrap must be root-owned and not group/world writable')
        return str(installed)
    raise RuntimeError('Install bubblewrap in the Linux execution environment; no unsandboxed fallback exists')


def provision():
    """Install an exact Ubuntu archive locally, checked against APT metadata."""
    package = 'bubblewrap=' + PACKAGE_VERSION
    metadata = subprocess.run(['apt-cache', 'show', package], capture_output=True,
                              text=True, check=True, timeout=30).stdout
    expected = [line.split(': ', 1)[1] for line in metadata.splitlines() if line.startswith('SHA256: ')]
    if len(set(expected)) != 1:
        raise RuntimeError('No unambiguous APT archive digest for pinned bubblewrap package')
    destination = Path.home() / '.local/share/mathtrace/bubblewrap' / PACKAGE_VERSION
    with tempfile.TemporaryDirectory(prefix='mathtrace-bwrap-') as directory:
        stage = Path(directory)
        subprocess.run(['apt-get', 'download', package], cwd=stage, capture_output=True,
                       check=True, timeout=120)
        archives = list(stage.glob('*.deb'))
        if len(archives) != 1 or sha(archives[0]) != expected[0]:
            raise RuntimeError('Downloaded bubblewrap archive does not match APT digest')
        subprocess.run(['dpkg-deb', '-x', str(archives[0]), str(stage / 'unpacked')],
                       capture_output=True, check=True, timeout=30)
        executable = stage / 'unpacked/usr/bin/bwrap'
        receipt = {'package': package, 'archive_sha256': expected[0], 'binary_sha256': sha(executable),
                   'trust': 'Local APT repository metadata and Ubuntu package; no root installation',
                   'path': str(destination / 'bwrap')}
        destination.mkdir(parents=True, exist_ok=True)
        if (destination / 'bwrap').exists() and sha(destination / 'bwrap') != receipt['binary_sha256']:
            raise RuntimeError('Existing local binary differs from verified package; inspect before replacing')
        if not (destination / 'bwrap').exists():
            shutil.copy2(executable, destination / 'bwrap')
        (destination / 'provenance.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        with keyring_filter():
            pass
        return receipt


def host_path(value):
    if len(value) > 2 and value[1:3] in {':\\', ':/'}:
        value = subprocess.run(['/usr/bin/wslpath', '-a', value], capture_output=True,
                               text=True, check=True, timeout=15).stdout.strip()
    return Path(value).resolve()


def stage_tree(specification, destination):
    """Only verified copied bytes enter the job; live host roots are never mounted."""
    if specification.get('archive') and specification.get('release_digest'):
        # Reuse the owned archive-exact extractor on the Linux filesystem.
        # This avoids per-file Windows/WSL copying without weakening manifests.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from mathtrace.toolchain import extract_distribution
        destination.mkdir()
        root, files, _ = extract_distribution(host_path(specification['archive']), destination,
            specification['release_digest'].removeprefix('sha256:'), target_platform='linux')
        if files != specification['files']:
            raise RuntimeError('Archive stage differs from the registered toolchain manifest')
        for name in files:
            (root / name).chmod(0o500 if name.startswith('bin/') else 0o400)
        return root
    root = host_path(specification['root'])
    expected = specification['files']
    actual = {}
    for path in root.rglob('*'):
        if path.is_symlink():
            raise RuntimeError('Symlink in formal input tree')
        if path.is_file():
            actual[path.relative_to(root).as_posix()] = path
    if set(actual) != set(expected):
        raise RuntimeError('Formal input file set differs from declared manifest')
    destination.mkdir()
    for name, path in actual.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target, follow_symlinks=False)
        if target.is_symlink() or sha(target) != expected[name]:
            raise RuntimeError('Staged formal input differs from declared bytes')
        target.chmod(0o500 if name.startswith('bin/') else 0o400)
    return destination


def collect_olean(path, *, directory_fd=None, limit=16 * 1024 * 1024):
    """Read one bounded regular output after the namespace has terminated."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    except FileNotFoundError:
        return None
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise RuntimeError('Compiled output is not a bounded regular file')
        content = stream.read(limit + 1)
        if len(content) > limit:
            raise RuntimeError('Compiled output exceeded the retention limit')
        return {'encoding': 'base64', 'sha256': hashlib.sha256(content).hexdigest(),
                'size': len(content), 'content': base64.b64encode(content).decode('ascii')}


def collect_compiled_files(directory_fd):
    """Retain the fixed Lean output family, including explicit absent parts."""
    files = {name: collect_olean(name, directory_fd=directory_fd) for name in COMPILED_FILES}
    manifest = {name: ({'sha256': blob['sha256'], 'size': blob['size']} if blob else None)
                for name, blob in files.items()}
    if sum(item['size'] for item in manifest.values() if item) > 64 * 1024 * 1024:
        raise RuntimeError('Compiled output family exceeded its aggregate retention limit')
    return files['Main.olean'], {name: blob for name, blob in files.items()
                                 if name != 'Main.olean' and blob is not None}, manifest


def formal(request):
    with tempfile.TemporaryDirectory(prefix='mathtrace-formal-') as directory:
        stage = Path(directory)
        toolchain = stage_tree(request['toolchain'], stage / 'toolchain')
        mounts = [(toolchain, '/toolchain', True)]
        library_names = []
        for index, library in enumerate(request['libraries']):
            name = '/libraries/' + str(index)
            mounts.append((stage_tree(library, stage / ('library-' + str(index))), name, True))
            library_names.append(name)
        environment = {'LEAN_SYSROOT': '/toolchain', 'LEAN_PATH': ':'.join(library_names), 'LEAN_NUM_THREADS': '2'}
        version = run({**request, 'timeout': min(request['timeout'], 30)}, mounts=mounts,
                      guest_command=['/toolchain/bin/lean', '-j2', '--version'], extra_environment=environment,
                      address_space_bytes=8 * 1024**3)
        if version['exit_code'] != 0:
            raise RuntimeError('Isolated Lean version check failed: ' + version['stderr'])
        result = run(request, mounts=mounts,
                     guest_command=['/toolchain/bin/lean', '-j2', '-o', '/outputs/Main.olean', '/inputs/Main.lean'],
                     extra_environment=environment, address_space_bytes=8 * 1024**3,
                     working_directory='/inputs', retain_output=True)
        compiled = result.pop('compiled_output', None)
        compiled_parts = result.pop('compiled_parts', {})
        compiled_file_set = result.pop('compiled_file_set', None)
        collection_error = result.pop('artifact_collection_error', None)
        replay = None
        semantic_output, verification_binding, resolved_inputs, verification_error = None, None, None, None
        if compiled and result['exit_code'] == 0 and not result['timed_out'] and not result['output_limited']:
            replay_root = stage / 'replay'
            replay_root.mkdir()
            (replay_root / 'Main.olean').write_bytes(base64.b64decode(compiled['content'], validate=True))
            (replay_root / 'Main.olean').chmod(0o400)
            for name, blob in compiled_parts.items():
                path = replay_root / name
                path.write_bytes(base64.b64decode(blob['content'], validate=True))
                path.chmod(0o400)
            verification = request.get('verification')
            if verification is None:
                replay = run({**request, 'source': ''}, mounts=[*mounts, (replay_root, '/replay', True)],
                    guest_command=['/toolchain/bin/leanchecker', '--fresh', 'Main'],
                    extra_environment={**environment, 'LEAN_PATH': ':'.join(['/replay', *library_names])},
                    address_space_bytes=8 * 1024**3)
            else:
                replay = run({**request, 'source': verification['helper_source']},
                    mounts=[*mounts, (replay_root, '/replay', True)],
                    guest_command=['/toolchain/bin/lean', '-j2', '--run', '/inputs/Main.lean',
                        '--verify-retained', 'Main', verification['check_symbol'], '/replay', *library_names],
                    extra_environment={**environment, 'LEAN_PATH': ''}, working_directory='/inputs',
                    address_space_bytes=8 * 1024**3, retain_output=True, retained_kind='semantics')
                semantic_output = replay.pop('semantic_output', None)
                replay.pop('compiled_output', None)
                replay.pop('compiled_parts', None)
                replay.pop('compiled_file_set', None)
                verification_binding = {'protocol': verification['protocol'], 'profile': verification['profile'],
                    'check_symbol': verification['check_symbol'],
                    'helper_sha256': hashlib.sha256(verification['helper_source'].encode()).hexdigest(),
                    'source_sha256': hashlib.sha256(request['source'].encode()).hexdigest(),
                    'compiled_file_set_hash': json_hash(compiled_file_set)}
                if semantic_output and replay['exit_code'] == 0 and not replay['timed_out'] and not replay['output_limited']:
                    try:
                        report = json.loads(base64.b64decode(semantic_output['content'], validate=True))
                        input_roots = {'/toolchain': (toolchain, request['toolchain']['files'])}
                        input_roots.update({name: (mounts[index + 1][0], library['files'])
                                            for index, (name, library) in enumerate(zip(library_names, request['libraries']))})
                        input_roots['/replay'] = (replay_root,
                            {name: item['sha256'] for name, item in compiled_file_set.items() if item})
                        resolved_inputs = bind_resolution(report['resolution'], input_roots, library_names)
                    except (ValueError, TypeError, KeyError, RecursionError, OSError) as error:
                        verification_error = str(error)
        return {'version': version, 'result': result, 'compiled_output': compiled,
                'compiled_parts': compiled_parts, 'compiled_file_set': compiled_file_set,
                'artifact_collection_error': collection_error, 'replay': replay,
                'semantic_output': semantic_output, 'verification_binding': verification_binding,
                'resolved_inputs': resolved_inputs, 'verification_error': verification_error}


def bind_resolution(resolution, roots, library_names):
    """Bind Lean's reconstructed resolution to actual immutable staged bytes."""
    from pathlib import PurePosixPath
    expected_paths = ['/replay', *library_names, '/toolchain/lib/lean']
    if (resolution.get('reference_search_roots') != ['/toolchain/lib/lean']
            or resolution.get('candidate_search_roots') != expected_paths
            or resolution.get('explicit_candidate_roots') != ['/replay', *library_names]):
        raise ValueError('Helper search roots do not match the committed input order')

    def file_binding(value, *, reference=False, optional=False):
        path = PurePosixPath(value)
        if not path.is_absolute() or '..' in path.parts or path.as_posix() != value or '\\' in value:
            raise ValueError('Unbound resolved input path')
        for prefix, (directory, manifest) in roots.items():
            if value.startswith(prefix + '/'):
                if reference and prefix != '/toolchain':
                    raise ValueError('Reference profile resolved outside the official distribution')
                relative = value[len(prefix) + 1:]
                if relative not in manifest:
                    if optional:
                        return None
                    raise ValueError('Resolved module part is not a declared staged input')
                actual = directory / relative
                if not actual.is_file() or actual.is_symlink() or sha(actual) != manifest[relative]:
                    raise ValueError('Resolved staged part does not match its exact manifest')
                return {'root': prefix, 'relative': relative, 'sha256': manifest[relative], 'size': actual.stat().st_size}
        raise ValueError('Resolved module is outside the declared input roots')

    result = {'channel': 'Lean resolution reconstructed under immutable roots and checked against staged bytes',
              'reference_search_roots': resolution['reference_search_roots'],
              'candidate_search_roots': expected_paths, 'import_mode': resolution['import_mode']}
    for scope in ('reference', 'candidate'):
        entries, seen = [], set()
        if not isinstance(resolution.get(scope), list) or not resolution[scope]:
            raise ValueError('Resolved module manifest is incomplete')
        for entry in resolution[scope]:
            identity = json.dumps(entry['module'], separators=(',', ':'))
            if identity in seen:
                raise ValueError('Duplicate resolved module identity')
            seen.add(identity)
            base = entry['base']
            if not base.endswith('.olean'):
                raise ValueError('Resolved module base is not an object')
            reference = scope == 'reference'
            server = file_binding(base + '.server', reference=reference, optional=True)
            private = file_binding(base + '.private', reference=reference, optional=True) if server else None
            ir = file_binding(base[:-6] + '.ir', reference=reference, optional=True)
            expected = {'olean': base, 'server': base + '.server' if server else None,
                'private': base + '.private' if private else None, 'ir': base[:-6] + '.ir' if ir else None}
            if entry['parts'] != expected:
                raise ValueError('Reported part presence differs from staged resolution')
            entries.append({'module': entry['module'], 'parts': {
                'olean': file_binding(base, reference=reference), 'server': server, 'private': private, 'ir': ir}})
        result[scope] = entries
    if not any(e['parts']['olean']['root'] == '/replay'
               and e['parts']['olean']['relative'] == 'Main.olean' for e in result['candidate']):
        raise ValueError('Target object is absent from actual resolved inputs')
    result['imported_bytes_retained_in_canonical_state'] = False
    return result


def run(request, *, mounts=(), guest_command=None, extra_environment=None, address_space_bytes=2 * 1024**3,
        working_directory='/work', retain_output=False, retained_kind='compiled'):
    if retained_kind not in {'compiled', 'semantics'}:
        raise ValueError('Unknown trusted retained-output family')
    timeout = request['timeout']
    if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 86400:
        raise ValueError('Invalid sandbox timeout')
    bwrap = bubblewrap()
    runtime = Path('/usr/bin/python3').resolve()
    identity = {'backend': 'bubblewrap-linux-v1', 'kernel': platform.release(),
                'bubblewrap_hash': sha(bwrap), 'interpreter_hash': sha(runtime),
                'recorder_hash': sha(__file__)}
    with tempfile.TemporaryDirectory(prefix='mathtrace-job-') as directory:
        inputs = Path(directory) / 'inputs'
        inputs.mkdir()
        (inputs / 'program.py').write_text(request['source'], encoding='utf-8')
        (inputs / 'Main.lean').write_text(request['source'], encoding='utf-8')
        (inputs / 'inputs.json').write_text(json.dumps(request.get('inputs', {}), allow_nan=False), encoding='utf-8')
        guest_command = guest_command or [str(runtime), '-I', '/inputs/program.py']
        export_parent = export_child = None
        launched_command = guest_command
        if retain_output:
            export_parent, export_child = socket.socketpair()
            bootstrap = ('import array,os,socket,sys\n'
                         's=socket.socket(fileno=int(sys.argv[1]))\n'
                         'fd=os.open("/outputs",os.O_RDONLY|os.O_DIRECTORY)\n'
                         's.sendmsg([b"O"],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array("i",[fd]))])\n'
                         'os.close(fd);s.close()\n'
                         'os.execv(sys.argv[2],sys.argv[2:])\n')
            (inputs / 'bootstrap.py').write_text(bootstrap, encoding='utf-8')
            identity['output_bootstrap_hash'] = hashlib.sha256(bootstrap.encode()).hexdigest()
            launched_command = [str(runtime), '-I', '/inputs/bootstrap.py', str(export_child.fileno()), *guest_command]
        command = [bwrap, '--unshare-all', '--unshare-user', '--disable-userns', '--die-with-parent',
                   '--new-session', '--cap-drop', 'ALL', '--clearenv',
                   '--ro-bind', '/usr', '/usr', '--tmpfs', '/usr/local', '--remount-ro', '/usr/local',
                   '--symlink', 'usr/bin', '/bin', '--symlink', 'usr/lib', '/lib',
                   '--symlink', 'usr/lib64', '/lib64',
                   '--proc', '/proc', '--remount-ro', '/proc', '--dev', '/dev', '--remount-ro', '/dev',
                   '--ro-bind', str(inputs), '/inputs',
                   '--size', str(128 * 1024 * 1024), '--tmpfs', '/work',
                   '--symlink', '/inputs/inputs.json', '/work/inputs.json',
                   '--size', str(128 * 1024 * 1024), '--tmpfs', '/tmp',
                   '--size', str(128 * 1024 * 1024), '--tmpfs', '/outputs',
                   '--chdir', working_directory, '--setenv', 'PATH', '/usr/bin',
                   '--setenv', 'HOME', '/work', '--setenv', 'LANG', 'C.UTF-8',
                   ]
        for source, target, readonly in mounts:
            command += ['--ro-bind' if readonly else '--bind', str(source), target]
        for name, value in (extra_environment or {}).items():
            command += ['--setenv', name, value]
        command += ['--remount-ro', '/', '--', *launched_command]

        def limits():
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_AS, (address_space_bytes, address_space_bytes))
            resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024**2, 128 * 1024**2))
            resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
            resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
            resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(timeout) + 1, math.ceil(timeout) + 1))

        started = time.monotonic()
        info = tempfile.TemporaryFile()
        seccomp = keyring_filter()
        identity['seccomp_filter_hash'] = hashlib.sha256(seccomp.read()).hexdigest()
        seccomp.seek(0)
        command[1:1] = ['--info-fd', str(info.fileno()), '--seccomp', str(seccomp.fileno())]
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, close_fds=True, start_new_session=True,
                                   preexec_fn=limits, pass_fds=(info.fileno(), seccomp.fileno(),
                                       *((export_child.fileno(),) if export_child else ())))
        LIVE_PROCESSES.add(process)
        seccomp.close()
        if export_child:
            export_child.close()
        directory_fd = None
        captured = {'stdout': bytearray(), 'stderr': bytearray()}
        timed_out = output_limited = False
        total = 0
        with selectors.DefaultSelector() as selector:
            if export_parent:
                selector.register(export_parent, selectors.EVENT_READ, 'directory')
            for stream, name in ((process.stdout, 'stdout'), (process.stderr, 'stderr')):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map():
                if time.monotonic() - started >= timeout or output_limited:
                    timed_out = not output_limited
                    break
                for key, _ in selector.select(min(0.05, max(0, timeout - (time.monotonic() - started)))):
                    if key.data == 'directory':
                        marker, ancillary, _, _ = export_parent.recvmsg(1, socket.CMSG_SPACE(array.array('i').itemsize))
                        descriptors = array.array('i')
                        for level, kind, values in ancillary:
                            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                                descriptors.frombytes(values[:len(values) - len(values) % descriptors.itemsize])
                        if marker == b'O' and len(descriptors) == 1:
                            directory_fd = descriptors[0]
                            os.set_inheritable(directory_fd, False)
                        else:
                            for descriptor in descriptors:
                                os.close(descriptor)
                        selector.unregister(export_parent)
                        export_parent.close()
                        continue
                    data = os.read(key.fileobj.fileno(), 65536)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    room = OUTPUT_LIMIT - total
                    captured[key.data].extend(data[:room])
                    total += len(data[:room])
                    if len(data) > room:
                        output_limited = True
                        break
        if timed_out or output_limited:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            exit_code = process.wait(timeout=max(0.1, timeout - (time.monotonic() - started)))
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            exit_code = process.wait()
        finally:
            process.stdout.close()
            process.stderr.close()
            if process.poll() is not None:
                LIVE_PROCESSES.discard(process)
        info.seek(0)
        raw_info = info.read(65536)
        info.close()
        launch_info = json.loads(raw_info) if raw_info else None
        compiled, compiled_parts, compiled_file_set, semantic_output, collection_error = None, {}, None, None, None
        if retain_output:
            if export_parent:
                export_parent.close()
            if directory_fd is None:
                collection_error = 'Trusted bootstrap did not deliver an output directory handle'
            else:
                try:
                    if retained_kind == 'semantics':
                        semantic_output = collect_olean(SEMANTIC_FILE, directory_fd=directory_fd, limit=64 * 1024 * 1024)
                    else:
                        compiled, compiled_parts, compiled_file_set = collect_compiled_files(directory_fd)
                except (OSError, RuntimeError) as error:
                    collection_error = str(error)
                finally:
                    os.close(directory_fd)
        return {'command': guest_command,
                **({'compiled_output': compiled, 'compiled_parts': compiled_parts,
                    'compiled_file_set': compiled_file_set,
                    'semantic_output': semantic_output,
                    'artifact_collection_error': collection_error} if retain_output else {}),
                'exit_code': None if timed_out else exit_code,
                'stdout': captured['stdout'].decode('utf-8', 'replace'),
                'stderr': captured['stderr'].decode('utf-8', 'replace'),
                'timed_out': timed_out, 'output_limited': output_limited,
                'duration_seconds': time.monotonic() - started, 'execution_environment': identity,
                'namespace_setup': launch_info,
                'declared_runtime_environment': extra_environment or {},
                'address_space_limit_bytes': address_space_bytes,
                'isolation_policy': {'network': 'none', 'host_workspace': 'not-mounted',
                    'kernel_keyrings': 'keyctl/add_key/request_key denied by seccomp',
                    'io_uring': 'io_uring_setup/enter/register denied by seccomp',
                    'vsock': 'socket(AF_VSOCK) and io_uring denied by seccomp',
                    'inputs': 'read-only /inputs', 'outputs': 'bounded stdout/stderr and optional retained regular .olean',
                    'additional_mounts': [{'path': target, 'read_only': readonly} for _, target, readonly in mounts],
                    'runtime': 'read-only /usr excluding /usr/local',
                    'writable_storage': 'ephemeral /work, /tmp and /outputs',
                    'resource_scope': 'per-process limits and bounded tmpfs; not aggregate cgroup accounting'}}


def json_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def atomic_observation(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def record(request):
    """Persist outside all guest mounts, before launch and after verified teardown."""
    request = dict(request)
    journal = request.pop('_journal', None)
    directory = started = None
    selected = request.get('execution_mode')
    protocol = request.get('execution_protocol')
    if journal is not None:
        if json_hash(request) != journal['request_hash']:
            raise RuntimeError('Recorder request differs from committed execution intent')
        directory = host_path(journal['directory'])
        directory.parent.mkdir(parents=True, exist_ok=True)
        directory.mkdir()  # An existing attempt directory never authorizes another launch.
        started = {'execution': journal['execution'], 'request_hash': journal['request_hash'],
            'pid': os.getpid(), 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'start_ticks': Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19],
            'recorder_hash': sha(__file__)}
        if protocol is not None:
            if selected != 'bubblewrap' or protocol != 'mode-aware-execution-v1':
                raise RuntimeError('Invalid sandbox execution mode/protocol')
            started.update(execution_mode=selected, execution_protocol=protocol)
        atomic_observation(directory / 'started.json', started)
    try:
        operation = request.get('operation')
        result = provision() if operation == 'provision' else formal(request) if operation == 'formal' else run(request)
        envelope = {'ok': True, 'result': result}
    except Exception as error:
        envelope = {'ok': False, 'error': str(error)}
    finally:
        # An error while reading streams must not leave a guest alive and then
        # publish a terminal certificate. Failure of cleanup leaves no certificate.
        for process in list(LIVE_PROCESSES):
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait(timeout=10)
            LIVE_PROCESSES.discard(process)
    if journal is not None:
        envelope.update({'execution': journal['execution'], 'request_hash': journal['request_hash'],
                         'producer': started, 'producer_hash': json_hash(started),
                         'teardown': 'recorder-owned-processes-waited'})
        if protocol is not None:
            envelope.update(execution_mode=selected, execution_protocol=protocol)
        atomic_observation(directory / 'terminal.json', envelope)
    return envelope


if __name__ == '__main__':
    try:
        envelope = record(json.load(sys.stdin))
    except Exception as error:
        envelope = {'ok': False, 'error': str(error)}
    print(json.dumps(envelope))
    sys.exit(0 if envelope['ok'] else 2)
