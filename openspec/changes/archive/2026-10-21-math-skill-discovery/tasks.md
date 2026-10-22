# Tasks

## 1. Native entry-point discovery

- [x] 1.1 Add direct project-root guide reading to only `math-intake` and `math-progress` in `mathtrace/native.py`, retaining protocol reading, existing mandates, request scope, and discretionary skill selection. Extend `tests/test_native.py` to verify these instructions, unchanged `mathtrace-help` behavior, and unchanged specialist/protocol/guide output; run the focused native tests.
- [x] 1.2 Regenerate the managed `.agents` projection using `python tools/install_native.py`; verify the two installed skills point to the existing `.agents/math/help.md`, managed manifests remain consistent, and external OpenSpec assets and unrelated agent/skill content are preserved through the installer checks.

## 2. Shared harness discovery and Codex preservation

- [x] 2.1 Add equivalent direct guide-reading instructions to the two maintained `coding-harnesses/shared/skills/` definitions, using project-root shared paths and preserving their mandates. Extend `tests/test_harness_payloads.py` to check discovery and resolve both entry-point forwarding chains against the complete `research.json` harness inventory, including both Codex skill locations and externally loaded skills; run the focused harness tests.
- [x] 2.2 Verify existing adapter wrappers deliver the changed shared instructions without unnecessary rewrites; run renderer repeatability and owner-customization checks in an isolated copy, confirming Codex paired agents, both skill directories, argument handling, host bindings, and preservation guards remain intact. Verify specialist prompts acquire no discovery or orchestration instruction.

## 3. Targeted Antigravity snapshot refresh

- [x] 3.1 Refresh only the Antigravity snapshot's intake and progress guidance with the native project-root guide path, preserving their existing mandates; reconcile only corresponding integrity entries where applicable. Extend the harness tests to resolve both snapshot references and verify relevant integrity entries; compare before/after files to confirm unrelated snapshot assets, existing metadata differences, and historical origin records are preserved. Run the focused harness tests, including the check that ordinary rendering leaves Antigravity untouched.

## 4. Integration verification

- [x] 4.1 Run `python -m pytest tests` and `python tools/validate_package.py`; resolve regressions and report results, verifying this instruction-only change preserves mathematical verification and release invariants.
- [x] 4.2 Run `openspec validate math-skill-discovery --strict` and `openspec validate --all`; review the final changed-file set against this design and report full harness coverage, resolved guide paths, and preservation results before marking implementation complete.
