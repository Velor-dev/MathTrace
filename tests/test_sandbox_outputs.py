"""Integration checks for retained sandbox output collection."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
import unittest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
LOCAL_BWRAP = ".local/share/mathtrace/bubblewrap/0.9.0-1ubuntu0.1/bwrap"


def backend_available() -> bool:
    """Detect the Linux execution backend used by the retained-output tests."""
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
            f"test -x /usr/bin/python3 && (test -x /usr/bin/bwrap || test -x $HOME/{LOCAL_BWRAP})",
        ]
        try:
            subprocess.run(probe, check=True, capture_output=True, timeout=10)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False
        return True
    if sys.platform == "linux":
        return bool(shutil.which("bwrap") or (Path.home() / LOCAL_BWRAP).is_file())
    return False


def _linux_package_root() -> str:
    """Return the repository path as seen by the Linux recorder."""
    if os.name != "nt":
        return str(PACKAGE_ROOT)
    converted = subprocess.run(
        ["wsl.exe", "-d", "Ubuntu", "--exec", "/usr/bin/wslpath", "-a", str(PACKAGE_ROOT)],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return converted.stdout.strip()


def _run_retaining_output(source: str) -> dict:
    """Call sandbox_runtime.run inside Ubuntu so its real bwrap is exercised."""
    package_root = _linux_package_root()
    runner = textwrap.dedent(
        f"""
        import json
        import sys
        sys.path.insert(0, {package_root!r})
        from mathtrace.sandbox_runtime import run

        request = json.load(sys.stdin)
        result = run(
            request,
            guest_command=["/usr/bin/python3", "-I", "/inputs/program.py"],
            retain_output=True,
        )
        print(json.dumps(result))
        """
    )
    command = [sys.executable, "-c", runner]
    if os.name == "nt":
        command = ["wsl.exe", "-d", "Ubuntu", "--exec", "/usr/bin/python3", "-c", runner]
    observed = subprocess.run(
        command,
        input=json.dumps({"source": source, "timeout": 5}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if observed.returncode:
        raise AssertionError(
            f"Linux retained-output runner failed ({observed.returncode}): "
            f"stdout={observed.stdout!r} stderr={observed.stderr!r}"
        )
    try:
        return json.loads(observed.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(
            f"Linux retained-output runner returned invalid JSON: "
            f"stdout={observed.stdout!r} stderr={observed.stderr!r}"
        ) from error


@unittest.skipUnless(backend_available(), "requires WSL Ubuntu with the installed bubblewrap backend")
class RetainedOutputIntegrationTests(unittest.TestCase):
    def test_atomically_renamed_regular_output_is_retained(self):
        source = textwrap.dedent(
            """
            import os

            payload = b'atomic-retained-output'
            temporary = '/outputs/Main.olean.tmp'
            with open(temporary, 'wb') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, '/outputs/Main.olean')
            print('done', flush=True)
            """
        )
        result = _run_retaining_output(source)

        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(result["timed_out"])
        self.assertFalse(result["output_limited"])
        self.assertIsNone(result["artifact_collection_error"])
        compiled = result["compiled_output"]
        self.assertIsNotNone(compiled)
        payload = b"atomic-retained-output"
        self.assertEqual(compiled["encoding"], "base64")
        self.assertEqual(compiled["size"], len(payload))
        self.assertEqual(compiled["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(base64.b64decode(compiled["content"]), payload)

    def test_compiled_family_retains_present_parts_and_explicit_absence(self):
        source = "from pathlib import Path\nfor name in ['Main.olean', 'Main.olean.server', 'Main.ir']:\n    Path('/outputs', name).write_bytes(name.encode())\n"
        result = _run_retaining_output(source)
        self.assertEqual(result['exit_code'], 0)
        self.assertIsNone(result['artifact_collection_error'])
        self.assertEqual(set(result['compiled_file_set']),
                         {'Main.olean', 'Main.olean.server', 'Main.olean.private', 'Main.ir'})
        self.assertIsNone(result['compiled_file_set']['Main.olean.private'])
        for name in ['Main.olean.server', 'Main.ir']:
            self.assertEqual(base64.b64decode(result['compiled_parts'][name]['content']), name.encode())
            self.assertEqual(result['compiled_file_set'][name]['sha256'], hashlib.sha256(name.encode()).hexdigest())

    def test_invalid_supplementary_part_rejects_the_whole_collection(self):
        source = "from pathlib import Path\nPath('/outputs/Main.olean').write_bytes(b'main')\nPath('/outputs/Main.olean.private').symlink_to('/inputs/Main.lean')\n"
        result = _run_retaining_output(source)
        self.assertEqual(result['exit_code'], 0)
        self.assertIsNone(result['compiled_output'])
        self.assertEqual(result['compiled_parts'], {})
        self.assertIsNone(result['compiled_file_set'])
        self.assertIsInstance(result['artifact_collection_error'], str)

    def test_export_socket_and_output_directory_descriptors_are_closed_before_exec(self):
        source = textwrap.dedent(
            """
            import json
            import os

            descriptors = {}
            for name in os.listdir('/proc/self/fd'):
                descriptor = int(name)
                if descriptor < 3:
                    continue
                try:
                    descriptors[name] = os.readlink('/proc/self/fd/' + name)
                except OSError:
                    pass
            print(json.dumps(descriptors), flush=True)
            """
        )
        result = _run_retaining_output(source)

        self.assertEqual(result["exit_code"], 0)
        descriptors = json.loads(result["stdout"])
        self.assertFalse(
            any(target.startswith("socket:") for target in descriptors.values()),
            descriptors,
        )
        self.assertFalse(
            any("/outputs" in target for target in descriptors.values()),
            descriptors,
        )

    def test_symlink_output_is_rejected_without_retaining_target_bytes(self):
        source = textwrap.dedent(
            """
            import os

            os.symlink('/inputs/Main.lean', '/outputs/Main.olean')
            """
        )
        result = _run_retaining_output(source)

        self.assertEqual(result["exit_code"], 0)
        self.assertIsNone(result["compiled_output"])
        self.assertIsInstance(result["artifact_collection_error"], str)

    def test_fifo_output_is_rejected_without_blocking_collection(self):
        source = textwrap.dedent(
            """
            import os

            os.mkfifo('/outputs/Main.olean')
            """
        )
        result = _run_retaining_output(source)

        self.assertEqual(result["exit_code"], 0)
        self.assertIsNone(result["compiled_output"])
        self.assertIsInstance(result["artifact_collection_error"], str)


if __name__ == "__main__":
    unittest.main()
