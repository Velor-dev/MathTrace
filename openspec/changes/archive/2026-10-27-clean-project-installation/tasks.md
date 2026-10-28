# Tasks

## 1. File mapping relocation and project root cleanliness

- [x] 1.1 Update `npm/lib/install.cjs` mapping logic to eliminate `coding-harnesses/` from the target project root, relocating necessary shared guidance/policy files under `.mathtrace/shared/`
- [x] 1.2 Update link rebinding in `npm/lib/install.cjs` to ensure markdown references point to `.mathtrace/shared/` instead of `coding-harnesses/shared/`
- [x] 1.3 Update tests in `npm/test/` to assert that `coding-harnesses/` is absent from the target project root and shared references resolve properly

## 2. Interactive console provisioning progress

- [x] 2.1 Add clear console progress status messages in `npm/lib/install.cjs` before venv creation, wheel installation, Lean 4 toolchain provisioning, and state initialization
- [x] 2.2 Ensure progress messages do not corrupt machine-readable output when `--json` or non-interactive mode is requested
- [x] 2.3 Run `npm test --prefix npm` to verify all installer unit tests pass with the new progress output

## 3. Version bump and validation

- [x] 3.1 Bump version to 0.1.2 across `npm/package.json`, `pyproject.toml`, `mathtrace/__init__.py`, and `uv.lock`
- [x] 3.2 Run regression test suite (`tests/test_package.py`, `tests/test_npm.py`, and `tools/validate_package.py`)
- [x] 3.3 Validate OpenSpec change with `openspec validate --all`

## Workflow follow-up

- Review and apply changes via `/openspec-apply-change`
- Build release package with `python tools/build_npm.py`
- Archive change and push commits to GitHub
- Publish updated package `mathtrace@0.1.2` to npm registry
