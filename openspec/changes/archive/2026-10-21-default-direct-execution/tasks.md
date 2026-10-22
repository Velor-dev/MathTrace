# Tasks

## 1. Versioned evidence and immutable execution selection

- [x] 1.1 Add explicit historical and new mode-aware protocol handling in `formal.py`, `evidence.py`, `research.py` and `context.py`, preserving original v1 writers/validators and pre-profile legacy ineligibility; verify historical checked receipts, missing namespace rejection, old pending recovery and unchanged candidate eligibility with retained fixtures in `test_formal.py` and `test_execution.py`.
- [x] 1.2 Add the single `execution_mode` argument and small dispatcher for computation, formal execution and toolchain installation; bind resolved mode/protocol into new requests before launch and preserve omitted-mode historical recovery; verify default/explicit/invalid mode, conflicting repeated request, deliberate rerun and no-fallback cases through API and CLI tests.
- [x] 1.3 Document mode selection, request compatibility, explicit sandbox setup and the direct local-host trust boundary in `docs/execution.md` and existing CLI/help examples; verify documented JSON arguments are accepted and unavailable sandbox errors never launch direct workloads.

## 2. Native process execution and recovery

- [x] 2.1 Implement the native recorder using absolute runtime executables, isolated interpreter invocation, fresh work/input directories, controlled platform environments and bounded concurrent pipe reads; verify real Python execution, `inputs.json`, Unicode/space paths, ambient override removal, nonzero exits, 4 MiB combined output bounds and finite timeouts in native execution tests, and document actual platform limits in `docs/execution.md`.
- [x] 2.2 Implement lifecycle cleanup with POSIX sessions/process groups and the minimal Windows Job Object helper, plus portable producer identity and atomic journal publication; verify timeout/descendant cleanup, control-setup failure, recorder interruption, pending uncertainty, absence of unsupported termination assertions and exact-once recovery in `test_execution.py` and native platform tests.
- [x] 2.3 Separate computation observation classification from isolation status in `evidence.py`, retaining failed/timeout process facts and root source review; verify successful direct observations have isolation false, namespace failures remain failures for sandbox mode, and neither result automatically promotes or refutes a claim in `test_evidence.py`; update `docs/evidence.md` accordingly.

## 3. Native pinned Lean provisioning

- [x] 3.1 Extend `toolchain.py` target mapping for Windows x86-64, Linux x86-64/AArch64 and macOS x86-64/AArch64, preserving the existing Bubblewrap Linux target and rejecting incompatible/unsupported targets; verify deterministic OS/CPU asset fixtures, alias handling, missing publisher digests, modified files and wrong-backend rejection in `test_toolchain_install.py`.
- [x] 3.2 Preserve exact ZIP provenance and fresh-tree publication while supporting native executable names, required Unix executable permissions and distribution layouts; verify safe extraction, redirected/aliased path rejection and executable readiness with archive fixtures, and document the supported target matrix and pinned installation commands in `docs/evidence.md` and `README.md`.

## 4. Portable formal checking and evidence qualification

- [x] 4.1 Parameterize semantic output in `lean_inspector.lean` while retaining the original helper invocation behavior; implement native compile/retained-object/helper orchestration without changing the primitive profile, safe-declaration policy or standalone fresh-check semantics; verify modern proof/module-proof acceptance and sorry, invalid and kernel-bypass rejection through updated `tools/validate_lean.py` cases and formal tests.
- [x] 4.2 Add versioned native resolution descriptors and exact role/root/part binding in recorder and canonical validation, retaining v1 guest-root validation; verify spaces, Unicode, native separators, case rules, path traversal, redirects, wrong root order, missing parts, altered bytes and ambient/current-directory shadowing in `test_formal.py` and native formal tests, and document staged-byte versus enforced-immutability limits.
- [x] 4.3 Bind process outcome, mode, actual environment/limits, compiled family, helper, semantic capsule and terminal producer into new receipts/manifests; expose bounded assurance facts in `context.py`; verify forged isolation, protocol/mode mismatch, report spoofing, lost bindings and diagnostic-text leakage are rejected in `test_formal.py`, `formal_fixture.py` and `test_context.py`.
- [x] 4.4 Exercise existing formal inference, withdrawal, candidate freeze, nonparty audit and release paths for both versions and execution modes without relaxing gates; verify source/helper/toolchain/object withdrawal, unresolved counterexamples, incomplete fidelity/foundation reviews and changed audit witnesses still block eligibility in `test_formal.py`, `test_campaign.py` and related completion/adjudication tests; update `docs/evidence.md` to describe the preserved gates and checking limits.

## 5. Existing harness and documentation consistency

- [x] 5.1 Update only execution-related wording and stale `.planning` references in `mathtrace/native.py`, shared protocol/help/computationalist role and matching owned projections; verify exact maintained role bodies, unchanged specialist policies/inheritance and absence of mandatory sandbox/OpenSpec runtime dependencies using `test_native.py` and `test_harness_payloads.py`.
- [x] 5.2 Reconcile Codex generation/research/README with both existing wrapper locations and paired TOML/Markdown agents, preserving unrelated owner edits or reporting conflicts before replacement; verify deterministic regeneration in temporary fixtures, wrapper consistency, role headers, custom-content preservation and no execution-mode duplication in `test_harness_payloads.py`; preserve recent adapter-format changes and disclose existing capture limitations.
- [x] 5.3 Update root `AGENTS.md`, `README.md`, `docs/architecture/decisions.md`, execution navigation and validation-tool usage for direct defaults and optional Bubblewrap/WSL; verify instructions contain no unconditional sandbox prerequisite, no unsupported source-correspondence guarantee and no new harness-sandbox integration, installer or workflow requirements. Keep main specs unchanged until normal spec synchronization.

## 6. Integrated verification

- [x] 6.1 Run `python -m pytest tests`, `python tools/validate_package.py` and `openspec validate --all`; retain concise evidence of results, package/helper fidelity and any skipped platform checks in the change review material, and resolve regressions without widening scope.
- [x] 6.2 Validate real native Python and pinned Lean compilation, standalone fresh checking, checked-target inspection and receipt recovery on Windows, Linux and macOS, including the supported CPU matrix as hosts are available; record actual platform/architecture coverage and leave unavailable checks explicitly unvalidated rather than declaring cross-platform completion from mocks.
- [x] 6.3 Run the existing optional Linux Bubblewrap and Windows/WSL computation, seccomp, retained-output and formal checks with explicit mode selection; verify unchanged isolation behavior and retained historical receipt eligibility, and record unavailable backend coverage separately from native results.

## Workflow follow-up

- Present this planning change for owner review; implementation requires a subsequent explicit apply request.
- After implementation and review, use the existing spec-sync/archive workflow; narrowly align the formal evidence spec Purpose with native/default and optional sandbox behavior without changing the standard schema.
