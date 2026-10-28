# Tasks: Lean 4 Download Progress Bar

## 1. Python Download Progress Reporting

- [x] 1.1 Implement terminal download progress calculation and formatting in `mathtrace/toolchain.py` (transferred MB, total MB, percentage, rate in MB/s, ETA, and TTY/non-TTY handling) and verify via unit tests in `tests/test_toolchain_install.py`.
- [x] 1.2 Wire the progress reporter into the archive download loop in `mathtrace/toolchain.py` so that chunks update the progress bar on `sys.stderr` and clean up upon completion.

## 2. Node Installer Subprocess Stderr Streaming

- [x] 2.1 Update `npm/lib/prerequisites.cjs` and `npm/lib/install.cjs` to support streaming stderr live to the parent process during toolchain bootstrap while capturing stdout for JSON IPC.
- [x] 2.2 Update and execute `tests/test_npm.py` and npm tests to verify that provisioning emits live stderr progress without interfering with JSON results or receipts.

## 3. End-to-End Verification

- [x] 3.1 Execute full test suite (`python -m pytest tests`), package validation (`python tools/validate_package.py`), and spec validation (`openspec validate --all`).

## Workflow follow-up

- Archive change after validation.
- Publish updated version to npm if required.
