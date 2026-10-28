# Design

## Context

During project installation via `npx mathtrace`, the Lean 4 distribution archive (~742 MB, containing ~11,420 files) is downloaded, extracted into a temporary staging folder, verified against publisher digests, and atomically published to `.math/toolchains/<version>/distribution-<uuid>`.

Currently:
1. `mathtrace/toolchain.py` provides visual real-time progress for network downloading (`DownloadProgress`), but archive extraction (`extractall`) and full-tree disk SHA-256 validation proceed silently.
2. `npm/lib/bootstrap.py` communicates with `npm/lib/install.cjs` via JSON on stdout while stderr is streamed to the user's console.
3. Immediately after `install_lean` performs a complete SHA-256 verification of all 11,420 extracted files, `bootstrap.py` invokes `verify_toolchain(store.get(identifier))`, performing a redundant full-tree disk traversal and re-hashing all 11,420 files.
4. On Windows, writing and re-hashing thousands of small files under real-time antivirus scanning (Windows Defender) takes 30-50 seconds. Without user-facing console feedback, the terminal appears completely frozen.

## Goals / Non-Goals

**Goals:**
- Provide clear, user-facing status indicators on `sys.stderr` before and during toolchain extraction and SHA-256 validation.
- Remove redundant immediate `verify_toolchain` execution in `bootstrap.py` during fresh installation, cutting ~10-15 seconds of wasted I/O.
- Maintain 100% mathematical and cryptographic verification rigor: every extracted file continues to be strictly verified against the publisher digest.
- Preserve full `verify_toolchain` checks for existing cached installations and explicit `--verify` checks.

**Non-Goals:**
- Removing or weakening file integrity verification in `extract_distribution`.
- Adding third-party UI or terminal formatting dependencies.
- Modifying offline Lean execution or campaign audit gates.

## Decisions

### Decision 1: Output extraction and validation progress to `sys.stderr`
- **Choice**: Write user-visible extraction status lines directly to `sys.stderr` with `flush()`.
- **Rationale**: `bootstrap.py` outputs JSON to `sys.stdout` for `install.cjs` consumption. Emitting status lines to `sys.stderr` avoids corrupting the JSON communication channel while immediately rendering in the user's terminal (since `install.cjs` uses `stdio: ['pipe', 'pipe', 'inherit']`).
- **Alternatives considered**:
  - *Emitting via stdout*: Would break JSON deserialization in `npm/lib/install.cjs`.
  - *Adding IPC progress events*: Unnecessary complexity when stderr is already piped/inherited for progress reporting.

### Decision 2: Report distinct progress milestones for extraction and verification
- **Choice**: In `extract_distribution` (or wrapping `install_lean`), report distinct stages:
  - `-> Extracting Lean {version} toolchain ({count} files)...`
  - `-> Verifying toolchain integrity against archive manifest...`
  - `[✓] Verified and extracted Lean {version}`
- **Rationale**: File extraction and full-tree SHA-256 re-hashing are distinct phases with significant duration on NTFS. Users see precisely what operation is occurring and know that the process is actively working.

### Decision 3: Eliminate redundant `verify_toolchain` pass in `bootstrap.py`
- **Choice**: Remove `verify_toolchain(store.get(identifier))` in `bootstrap.py` immediately after `install_lean(...)`.
- **Rationale**: `extract_distribution` in `install_lean` already computes the SHA-256 digest of every extracted file on disk and verifies it against the archive manifest before atomically renaming the directory. Calling `verify_toolchain` milliseconds later on the exact same files is completely redundant and adds significant disk read latency.
- **Alternatives considered**:
  - *Skipping verification inside `extract_distribution` and relying solely on `verify_toolchain`*: Rejected because `extract_distribution` protects against corrupted staging before publishing to the active store.

## Risks / Trade-offs

- **[Risk]** Uncaught file corruption during fresh installation if secondary checks are removed.
  - **Mitigation**: `extract_distribution` already validates every file against the expected SHA-256 digest before directory staging completes. Furthermore, `install.cjs` continues to run `--verify` during post-deployment activation.
- **[Risk]** Windows console encoding errors with special symbols.
  - **Mitigation**: Use safe ASCII fallbacks (`[✓]` with fallback to `[OK]` or `->`), matching the pattern established in `DownloadProgress`.
