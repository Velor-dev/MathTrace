"""Integration checks for the real bubblewrap computation backend."""

from __future__ import annotations

import errno
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
import time
import unittest
from unittest.mock import patch

from mathtrace.sandbox import compute


OUTPUT_LIMIT = 4 * 1024 * 1024
LOCAL_BWRAP = ".local/share/mathtrace/bubblewrap/0.9.0-1ubuntu0.1/bwrap"


def backend_available() -> bool:
    """Detect the explicitly supported Linux execution backend only."""
    if os.name == "nt":
        if shutil.which("wsl.exe") is None:
            return False
        probe = [
            "wsl.exe",
            "-d",
            "Ubuntu",
            "--exec",
            "/bin/sh",
            "-lc",
            f"test -x /usr/bin/python3 && (command -v bwrap >/dev/null 2>&1 || test -x $HOME/{LOCAL_BWRAP})",
        ]
        try:
            subprocess.run(probe, check=True, capture_output=True, timeout=10)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False
        return True
    if sys.platform == "linux":
        return bool(shutil.which("bwrap") or (Path.home() / LOCAL_BWRAP).is_file())
    return False


@unittest.skipUnless(backend_available(), "requires WSL Ubuntu with the pinned bubblewrap backend")
class SandboxIntegrationTests(unittest.TestCase):
    def test_mount_network_environment_and_keyring_boundaries(self):
        source = textwrap.dedent(
            """
            import ctypes
            import errno
            import json
            import os
            from pathlib import Path
            import platform
            import socket

            host_paths = ["/mnt/c/Users", "/workspace", "/root/.ssh", "/root/.aws", "/run/secrets"]
            try:
                connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                connection.settimeout(0.4)
                connection.connect(("198.51.100.1", 9))
            except OSError as error:
                network = {"status": "denied", "errno": errno.errorcode.get(getattr(error, "errno", None))}
            else:
                network = {"status": "connected", "errno": None}
            finally:
                try:
                    connection.close()
                except UnboundLocalError:
                    pass

            syscall_numbers = {"x86_64": 250, "amd64": 250, "aarch64": 219}
            keyctl_number = syscall_numbers.get(platform.machine())
            if keyctl_number is None:
                keyring = {"supported": False}
            else:
                libc = ctypes.CDLL(None, use_errno=True)
                result = libc.syscall(keyctl_number, 0, 0, 0, 0, 0)
                keyring = {"supported": True, "result": result, "errno": ctypes.get_errno()}

            open_fds = []
            for descriptor in range(3, 64):
                try:
                    os.fstat(descriptor)
                except OSError:
                    continue
                open_fds.append(descriptor)
            print(json.dumps({
                "host_paths": {path: Path(path).exists() for path in host_paths},
                "network": network,
                "environment": dict(os.environ),
                "keyring": keyring,
                "open_fds": open_fds,
            }))
            """
        )
        with patch.dict(os.environ, {'MATHTRACE_TEST_CREDENTIAL': 'fixture-secret',
                                     'WSLENV': 'MATHTRACE_TEST_CREDENTIAL',
                                     'LD_PRELOAD': '/nonexistent-fixture-library.so'}):
            result = compute(source, {}, timeout=5)
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(result["timed_out"])
        self.assertFalse(result["output_limited"])
        observed = json.loads(result["stdout"])

        self.assertEqual(observed["host_paths"], {
            "/mnt/c/Users": False,
            "/workspace": False,
            "/root/.ssh": False,
            "/root/.aws": False,
            "/run/secrets": False,
        })
        self.assertEqual(observed["network"]["status"], "denied")
        self.assertIn(observed["network"]["errno"], {"ENETUNREACH", "EHOSTUNREACH", "ENETDOWN"})
        self.assertEqual(observed["environment"]["HOME"], "/work")
        self.assertEqual(observed["environment"]["PATH"], "/usr/bin")
        self.assertEqual(set(observed["environment"]) - {"HOME", "LANG", "PATH", "PWD"}, set())
        self.assertEqual(observed["open_fds"], [])
        self.assertTrue(observed["keyring"]["supported"])
        self.assertEqual(observed["keyring"]["result"], -1)
        self.assertEqual(observed["keyring"]["errno"], errno.EPERM)
        self.assertEqual(result["execution_environment"]["backend"], "bubblewrap-linux-v1")

    def test_input_and_runtime_are_read_only_while_work_and_tmp_are_writable(self):
        source = textwrap.dedent(
            """
            import json
            import os
            from pathlib import Path

            def can_open_for_append(path):
                try:
                    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND)
                except OSError:
                    return False
                os.close(descriptor)
                return True

            input_path = Path("/work/inputs.json")
            work_path = Path("/work/write-check")
            tmp_path = Path("/tmp/write-check")
            work_path.write_text("work", encoding="utf-8")
            tmp_path.write_text("tmp", encoding="utf-8")
            print(json.dumps({
                "input": json.loads(input_path.read_text(encoding="utf-8")),
                "input_is_symlink": input_path.is_symlink(),
                "input_can_open_for_append": can_open_for_append(input_path),
                "mounted_input_can_open_for_append": can_open_for_append("/inputs/inputs.json"),
                "runtime_can_open_for_append": can_open_for_append("/usr/bin/python3"),
                "work": work_path.read_text(encoding="utf-8"),
                "tmp": tmp_path.read_text(encoding="utf-8"),
            }))
            """
        )
        request_inputs = {"marker": "input-is-read-only"}
        result = compute(source, request_inputs, timeout=5)
        self.assertEqual(result["exit_code"], 0)
        observed = json.loads(result["stdout"])
        self.assertEqual(observed["input"], request_inputs)
        self.assertTrue(observed["input_is_symlink"])
        self.assertFalse(observed["input_can_open_for_append"])
        self.assertFalse(observed["mounted_input_can_open_for_append"])
        self.assertFalse(observed["runtime_can_open_for_append"])
        self.assertEqual(observed["work"], "work")
        self.assertEqual(observed["tmp"], "tmp")
        self.assertEqual(result["isolation_policy"]["inputs"], "read-only /inputs")
        self.assertEqual(result["isolation_policy"]["runtime"], "read-only /usr excluding /usr/local")

    def test_output_is_capped_at_four_megabytes(self):
        source = "import sys\nsys.stdout.write('x' * (4 * 1024 * 1024 + 1))\nsys.stdout.flush()\n"
        result = compute(source, {}, timeout=5)
        self.assertTrue(result["output_limited"])
        self.assertFalse(result["timed_out"])
        self.assertEqual(len(result["stdout"].encode("utf-8")), OUTPUT_LIMIT)
        self.assertEqual(result["stderr"], "")

    def test_timeout_kills_a_descendant_in_the_job_process_group(self):
        source = textwrap.dedent(
            """
            import json
            import os
            import subprocess
            import sys
            import time

            child = subprocess.Popen([
                sys.executable,
                "-c",
                "import time; token='MATHTRACE_SANDBOX_DESCENDANT'; time.sleep(60)",
            ], start_new_session=True)
            print(json.dumps({
                "child_pid": child.pid,
                "parent_process_group": os.getpgrp(),
                "child_process_group": os.getpgid(child.pid),
            }), flush=True)
            time.sleep(60)
            """
        )
        result = compute(source, {}, timeout=0.4)
        self.assertTrue(result["timed_out"])
        self.assertIsNone(result["exit_code"])
        self.assertFalse(result["output_limited"])
        observed = json.loads(result["stdout"])
        self.assertGreater(observed["child_pid"], 0)
        self.assertNotEqual(observed["parent_process_group"], observed["child_process_group"])

        if os.name == "nt":
            process_list_command = ["wsl.exe", "-d", "Ubuntu", "--exec", "/bin/ps", "-eo", "args"]
        else:
            process_list_command = ["ps", "-eo", "args"]
        process_list = ""
        for _ in range(10):
            process_list = subprocess.run(process_list_command, check=True, capture_output=True,
                                          text=True, timeout=5).stdout
            if "MATHTRACE_SANDBOX_DESCENDANT" not in process_list:
                break
            time.sleep(0.05)
        self.assertNotIn("MATHTRACE_SANDBOX_DESCENDANT", process_list)

    def test_af_vsock_socket_creation_is_denied(self):
        source = textwrap.dedent(
            """
            import errno
            import json
            import socket

            result = {}
            try:
                s = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
                result["status"] = "allowed"
                s.close()
            except OSError as error:
                result["status"] = "denied"
                result["errno"] = errno.errorcode.get(getattr(error, "errno", None))
            print(json.dumps(result))
            """
        )
        result = compute(source, {}, timeout=5)
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(result["timed_out"])
        observed = json.loads(result["stdout"])
        self.assertEqual(observed["status"], "denied")
        self.assertEqual(observed["errno"], "EPERM")

    def test_io_uring_setup_is_denied(self):
        source = textwrap.dedent(
            """
            import ctypes
            import errno
            import json

            libc = ctypes.CDLL(None, use_errno=True)
            # io_uring_setup is syscall 425 on x86_64 Linux
            res = libc.syscall(425, 1, 0)
            err = ctypes.get_errno()
            result = {
                "status": "allowed" if res >= 0 else "denied",
                "errno": errno.errorcode.get(err, str(err)),
            }
            print(json.dumps(result))
            """
        )
        result = compute(source, {}, timeout=5)
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(result["timed_out"])
        observed = json.loads(result["stdout"])
        self.assertEqual(observed["status"], "denied")
        self.assertEqual(observed["errno"], "EPERM")


class SeccompFilterIsolationTests(unittest.TestCase):
    @patch("ctypes.CDLL")
    def test_seccomp_filter_fails_closed_if_socket_syscall_unresolved(self, mock_cdll):
        mock_lib = mock_cdll.return_value
        mock_lib.seccomp_init.return_value = 12345
        mock_lib.seccomp_syscall_resolve_name.side_effect = lambda name: 1 if name != b'socket' else -1
        mock_lib.seccomp_rule_add_array.return_value = 0
        from mathtrace.sandbox_runtime import seccomp_filter
        with self.assertRaises(RuntimeError) as ctx:
            seccomp_filter()
        self.assertIn("Cannot resolve required socket syscall for AF_VSOCK denial", str(ctx.exception))

    @patch("ctypes.CDLL")
    def test_seccomp_filter_fails_closed_if_socket_rule_add_fails(self, mock_cdll):
        mock_lib = mock_cdll.return_value
        mock_lib.seccomp_init.return_value = 12345
        mock_lib.seccomp_syscall_resolve_name.return_value = 41
        # keyctl/add_key/request_key (3) + io_uring (3) succeed, socket rule returns -1
        mock_lib.seccomp_rule_add_array.side_effect = [0, 0, 0, 0, 0, 0, -1]
        from mathtrace.sandbox_runtime import seccomp_filter
        with self.assertRaises(RuntimeError) as ctx:
            seccomp_filter()
        self.assertIn("Cannot install required AF_VSOCK socket denial", str(ctx.exception))

    @patch("ctypes.CDLL")
    def test_seccomp_filter_fails_closed_if_io_uring_syscall_unresolved(self, mock_cdll):
        mock_lib = mock_cdll.return_value
        mock_lib.seccomp_init.return_value = 12345
        mock_lib.seccomp_syscall_resolve_name.side_effect = lambda name: -1 if name == b'io_uring_setup' else 1
        mock_lib.seccomp_rule_add_array.return_value = 0
        from mathtrace.sandbox_runtime import seccomp_filter
        with self.assertRaises(RuntimeError) as ctx:
            seccomp_filter()
        self.assertIn("Cannot install required io_uring denial for io_uring_setup", str(ctx.exception))

    @patch("ctypes.CDLL")
    def test_seccomp_filter_fails_closed_if_io_uring_rule_add_fails(self, mock_cdll):
        mock_lib = mock_cdll.return_value
        mock_lib.seccomp_init.return_value = 12345
        mock_lib.seccomp_syscall_resolve_name.return_value = 425
        # keyctl/add_key/request_key succeed (3 x 0), then first io_uring returns -1
        mock_lib.seccomp_rule_add_array.side_effect = [0, 0, 0, -1]
        from mathtrace.sandbox_runtime import seccomp_filter
        with self.assertRaises(RuntimeError) as ctx:
            seccomp_filter()
        self.assertIn("Cannot install required io_uring denial for io_uring_setup", str(ctx.exception))



