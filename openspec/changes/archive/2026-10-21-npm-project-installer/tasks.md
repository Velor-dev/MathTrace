# Tasks

## 1. Clean wheel build and full validation

- [x] 1.1 Make release/package validation build from fresh allowlisted source staging inputs, excluding stale `build/lib` and legacy `gsd_math` content without deleting retained archives. Add a dirty-build regression fixture and verify the resulting wheel contains only the intended package and valid metadata/notices; document the clean-build path with the packaging utility.
- [x] 1.2 Strengthen `tools/validate_package.py` to validate the complete wheel member set, safe unique paths, runtime/helper bytes, rights notices, version/entry-point metadata and RECORD checksums. Add rejection tests for injected legacy packages, extra files, duplicate/escaping entries and metadata mismatch; run those tests and verify isolated installed CLI identity outside the checkout.

## 2. Bundled npm release and selection interface

- [x] 2.1 Add the lightweight npm package and built-in-only installer entry point with Node 22+ support, a numbered menu from the complete harness inventory, explicit `--harness` selection, and documented Python 3.11+ prerequisites. Add menu/argument tests covering every selection, invalid input, EOF/cancellation and non-interactive input; verify no production npm dependencies or global-install requirement.
- [x] 2.2 Add release assembly that bundles one matching clean wheel, maintained/generated harness assets, full shared/documentation dependencies and unchanged rights notices with destination/hash metadata. Preserve source Antigravity provenance and Codex customizations; test version/hash mismatches and inspect an actual local npm tarball for required hidden assets and exclusion of secrets, campaign data, historical work and development-only skills. Document local packaging with publication disabled.

## 3. Project preflight and private runtime

- [x] 3.1 Implement project-root canonicalization, Python/version/venv/pip probing and selected execution-target checks, with no automatic Python installation or host provisioning. Add missing/old Python, unusable venv, platform, spaces-in-path and redirected-destination tests; document actionable prerequisites and verify failures leave active project files unchanged.
- [x] 3.2 Add small harness-specific external prerequisite checks using the existing inventory and supported setup contracts, including Pi extension compatibility, Hermes target skill-source binding and Claude instruction loading. Test satisfied/missing/unverifiable fixtures for the full inventory, verify no profile/home writes or secret logging, and update selected harness setup guidance with exact corrective setup and rerun steps.
- [x] 3.3 Install the bundled wheel into a private versioned environment at its final project-local path and provide the persistent runtime launcher using the owned interpreter and isolated module invocation. Test correct identity, argument/exit-code forwarding, conflicting ambient packages, missing base interpreter and moved-project diagnostics; verify the user's `.venv`, system packages and PATH remain unchanged and document the launcher.

## 4. Ownership-aware deployment and recovery

- [x] 4.1 Implement bounded installation receipts, complete destination preflight, exact ownership/hash comparison, a project lock and managed instruction-section merging. Test unowned/modified collisions, identical unowned files remaining unowned, malformed manifests, preserved surrounding instruction bytes, redirected paths and concurrent installs; document conflict handling.
- [x] 4.2 Implement staged payload writes, touched-file backups, a durable recovery journal and receipt-last activation. Add failure injection before/after replacement and activation, abrupt-interruption/retry coverage, and edited-file-during-recovery tests; verify previous active deployment is restored or precise recovery guidance is produced without overwriting subsequent user edits.
- [x] 4.3 Implement unchanged reinstall and same-harness updates with reuse of verified runtime environments and removal only of obsolete unchanged owned payload files. Test idempotence, retained prior runtime environments, foreign files, update conflicts and rejected incompatible harness switches; document retention and explicit recovery behavior without adding an automatic cleanup system.

## 5. Existing campaign and Lean provisioning

- [x] 5.1 Integrate existing default-store initialization only when absent, validate existing health/schema, and provision pinned Lean through existing APIs with verified-record reuse. Add fixtures for existing/missing/corrupt stores, valid/tampered toolchains, failed download/digest, retry after successful record creation and unchanged reinstall; verify no reinitialization, duplicate provisioning events or rewritten mathematical history. Document the initial database/toolchain side effects.
- [x] 5.2 Keep Direct Execution as default and implement explicit optional Bubblewrap provisioning selection through existing target/backend checks. Extend installer integration tests for Windows/Linux/macOS target selection, unsupported targets, missing sandbox prerequisites and no fallback; verify default installation does not probe WSL/Bubblewrap and document that operation JSON still explicitly selects optional Bubblewrap.

## 6. Complete harness deployment

- [x] 6.1 Deploy each inventory payload's native files and required shared/documentation closure with bounded runtime-command binding to the local launcher. Extend harness tests to install every payload in an unrelated project, resolve all required references and invoke the installed runtime without source or npm-package access; verify specialist role bytes, skill mandates, request boundaries, direct guide reading and host bindings remain intact. Update maintained installation guidance and installed link paths.
- [x] 6.2 Add focused preservation fixtures for customized Codex paired agents and both possible skill locations, managed Antigravity ownership, mutually exclusive OpenCode variants, existing project settings/docs and unrelated skills. Verify conflicts stop before replacement, duplicate skill wrappers are not auto-activated, fresh native role output matches the wheel renderer, and original provenance records remain untouched; document supported layout selection and source-install coexistence.

## 7. Packed artifact acceptance

- [x] 7.1 Exercise the actual packed npm artifact in fresh temporary projects with supported prerequisite fixtures, then remove access to the source and original npm package directory. Verify runtime identity, campaign health, guide resolution, safe reinstall/update and recovery for the complete harness inventory; run a real pinned Lean provisioning/check smoke test on the available supported host and report it separately from fixture coverage.
- [x] 7.2 Run `python -m pytest tests`, the installer Node test suite, `python tools/validate_package.py`, local npm artifact validation, `openspec validate npm-project-installer --strict`, and `openspec validate --all`; fix regressions and report platform coverage/limits, unchanged mathematical gates and rights-notice checks. Do not commit, publish, archive, or install into the owner's working project as part of acceptance.
