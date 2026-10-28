# Tasks

## 1. Minimalist Harness Menu & Direct Mode Enforcement

- [x] 1.1 Update `npm/lib/selection.cjs` to format harness menu items cleanly as `${i + 1}. ${h.name}` without duplicate parenthetical IDs, and verify menu output in `npm/test/selection.test.cjs`.
- [x] 1.2 Remove the `--execution-mode` option and bubblewrap validation from `npm/lib/selection.cjs` and `npm/bin/install.cjs`, setting `mode: 'direct'` as the sole default, and verify options parsing.

## 2. Eliminate Host CLI and Sandbox Probing

- [x] 2.1 Remove `P.sandbox()` and `P.external()` invocations from `npm/lib/install.cjs` so projects install cleanly without host CLI checks or WSL/libseccomp hanging.
- [x] 2.2 Clean up `npm/lib/prerequisites.cjs` by removing the `commands` executable table and host `--version` probing logic while keeping core Python and file integrity checks.
- [x] 2.3 Update `npm/test/prerequisites.test.cjs` and `npm/test/integration.test.cjs` to assert that harness installations succeed without requiring host CLI binaries.

## 3. Privacy, Git Hygiene & Legacy Cleanup

- [x] 3.1 Add `.mathtrace/` to `.gitignore` to guarantee local machine paths and deployment receipts cannot be committed to git, and verify with `git status`.
- [x] 3.2 Remove deprecated `.agents/workflows/*.md` files (`opsx-*.md`) now superseded by `.agents/skills/openspec-*`.

## 4. Verification & Validation

- [x] 4.1 Run `npm test --prefix npm` and verify all tests pass cleanly.
- [x] 4.2 Run `python tools/validate_package.py` and `python tools/build_npm.py` to ensure the npm artifact builds cleanly with valid manifest and hashes.
- [x] 4.3 Run `openspec validate --all` to verify all capability specifications and delta specs validate without errors.

## Workflow follow-up

- Archive the change after implementation and test verification are complete.
- Verify the archived capability spec.
