# Tasks

## 1. Extraction and Verification Status Feedback

- [x] 1.1 Add user-visible extraction and verification phase status messages to `sys.stderr` in `mathtrace/toolchain.py` (`extract_distribution`) and verify with a mock toolchain install test
- [x] 1.2 Update unit tests in `tests/test_toolchain_install.py` to assert extraction and validation progress messages are emitted to stderr during toolchain installation

## 2. Fresh Provisioning Optimization

- [x] 2.1 Update `npm/lib/bootstrap.py` to omit the redundant immediate `verify_toolchain` call during initial `install_lean` provisioning while preserving strict verification for cached toolchains and `--verify`
- [x] 2.2 Verify all toolchain tests pass via `uv run pytest tests/test_toolchain_install.py` and existing npm bridge tests via `node npm/test/prerequisites.test.cjs`

## 3. Package Build and OpenSpec Validation

- [x] 3.1 Run `python tools/validate_package.py` to ensure all packaging, linting, CLI, and npm bundle checks pass
- [x] 3.2 Run `openspec validate --all` to verify full coherence of OpenSpec changes and delta specifications
