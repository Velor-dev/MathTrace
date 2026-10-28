# Proposal

## Why

After downloading the ~742 MB Lean 4 distribution archive, the installation process pauses silently for 30 to 50 seconds on Windows. This silence is caused by unpacking over 11,000 files, real-time antivirus file scanning, and multiple redundant SHA-256 hashing passes across the entire uncompressed distribution tree (both inside `extract_distribution` and immediately afterward in `bootstrap.py` and `install.cjs`). Providing user-visible status during archive extraction/verification and removing redundant fresh-install verification passes will eliminate user confusion and accelerate toolchain provisioning.

## What Changes

- Add clear user-visible status progress reporting during toolchain extraction and integrity checking (e.g. indicating archive extraction and manifest verification).
- Streamline fresh toolchain installation in `npm/lib/bootstrap.py` by avoiding redundant immediate `verify_toolchain` passes when `install_lean` has already verified every extracted file against the publisher digest.
- Preserve complete and strict `verify_toolchain` verification for existing cached toolchains and explicit `--verify` audits to maintain mathematical gate integrity.

## Capabilities

### Modified Capabilities

- `project-installation`: Require visible progress during toolchain extraction and file verification, and ensure fresh provisioning performs single-pass extraction verification without redundant immediate re-hashing passes.

## Impact

- `mathtrace/toolchain.py`: Add user-visible feedback during archive extraction and post-extraction validation.
- `npm/lib/bootstrap.py`: Streamline fresh provisioning by omitting redundant immediate re-verification of just-extracted and verified toolchain trees.
- `tests/test_toolchain_install.py`: Verify that extraction and verification progress messages are emitted and fresh installation succeeds without redundant overhead.
