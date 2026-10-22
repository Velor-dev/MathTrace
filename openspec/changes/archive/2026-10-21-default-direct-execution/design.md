# Design

## Context

See `proposal.md` for motivation and the two delta specs for behavioral requirements. The exploration found these concrete boundaries:

- `evidence.py` imports `compute` and `check_lean` directly from `sandbox.py`. `Executions.begin` already commits launch intent before execution and supports exact recovery without retries.
- `sandbox.py` selects Linux Python or Ubuntu WSL; `sandbox_runtime.py` combines Linux transport, recording, resource limits, formal orchestration and output collection.
- `formal.process_passed` requires namespace integers, and both `_write_formal` and `receipt_evidence` call it. `_write_experiment` also treats missing namespaces as execution failure.
- Modern verification runs `lean_inspector.lean --verify-retained`, using pristine primitive-context replay and declaration comparison. The standalone path runs `leanchecker --fresh`. These are distinct existing protocols; plain fresh checking cannot replace the richer helper.
- Toolchain installation hardcodes Linux x86-64. ZIP extraction already supports Windows binary selection but does not restore Unix executable permissions. Semantic output and module-resolution validation hardcode guest paths.
- `research._formal_condition` and `context.py` compare a single receipt version; changing only that constant would invalidate historical receipts or hide new metadata. Candidate closure delegates to `receipt_evidence`.
- Codex has paired TOML/Markdown agents and both existing skill-wrapper locations. Renderer/research bindings currently target `.agents/skills`; the owner-maintained `.codex/skills` must survive. Recent `align-coding-harness-adapters` work must remain intact.

Current root instructions and evidence requirements mandate sandboxing and overstate source-to-object correspondence. Implementation must update the execution policy deliberately while preserving the actual checking, review and release guarantees. Main spec Purpose text still describing mandatory sandboxing will need a narrow wording correction when the approved delta is synchronized; planning does not edit main specs.

## Goals / Non-Goals

**Goals:** keep one root-mediated mathematical workflow; reuse the ledger, checked-target helper, manifests and recovery semantics; make execution mode an explicit recorded runtime fact; provide native execution on the pinned release's supported OS/CPU combinations.

**Non-Goals:** new sandbox backends, coding-harness sandbox integration, Codex capture/admission implementation, stronger host authentication, mathematical-method changes, new configuration files, backend plugin registries, npm installer development, unrelated adapter cleanup or changes to the standard OpenSpec schema.

## Decisions

### 1. One selector at existing operation boundaries

Add the optional JSON/Python argument `execution_mode` to `run_experiment`, `run_lean` and `install_lean`, accepting `direct` or `bubblewrap`. Omission selects `direct` for a new attempt or installation. Keep the CLI's existing JSON argument dispatch rather than add an environment/configuration precedence system or duplicate global flags. Document examples in the existing help/docs.

Resolve mode before toolchain validation or launch; include it and the execution-evidence protocol in each new committed request and fingerprint. A small dispatcher routes to the native recorder or existing sandbox transport. Retain `sandbox.py` as the explicit Bubblewrap interface, including `provision`; Direct Execution never invokes it to probe prerequisites. Unsupported modes fail before launch; explicit sandbox failures do not fall back.

For an existing attempt, omission means recover the exact attempt under its recorded mode, including pre-change sandbox attempts. An explicitly conflicting mode is rejected. Changing mode for an actual rerun requires the existing latest-terminal `rerun_of` and reason rules, plus a compatible toolchain. A new reviewed plan remains necessary for changed source or reviewed libraries.

Alternative rejected: harness-selected modes or separate skills. They duplicate policy and risk changing execution without binding the attempt.

### 2. Small native recorder, existing execution ledger

Use the installed runtime's absolute `sys.executable` for native Python and absolute verified executables for Lean. Execute argument arrays without a shell, in a fresh temporary work directory with explicit inputs, UTF-8 file handling and a controlled environment. Retain `inputs.json` in the computation working directory. Clear ambient Python/Lean and dynamic-loader overrides; retain only necessary platform environment entries, including Windows system/runtime requirements. Python isolated mode controls interpreter import behavior but is not a sandbox.

Reuse source/target review, execution intent, result envelopes, producer hashes and exact-once terminal import. Implement portable atomic journal publication with platform-appropriate durability; record OS/CPU, process identity, executable and recorder hashes without requiring `/proc` on native platforms. Start identity does not assert present liveness. Journals and temporary directories remain trusted local-host observations, not protection from same-user hostile code.

Use concurrent bounded stdout/stderr drains compatible with Windows pipes, preserving the existing combined 4 MiB limit and finite timeout validation. Cleanup precedes terminal publication. Use POSIX sessions/process-group cleanup on Linux/macOS and a small standard-library Windows process-control helper (a Job Object through `ctypes`, with assignment before workload execution) to own and wait for launched processes. This is lifecycle control, not AppContainer or a sandbox backend. Reject unsupported process-control setup instead of claiming teardown. State the limits of escaped POSIX descendants; unresolved cleanup leaves the attempt uncertain. Do not claim universal hostile process containment in direct mode.

Preserve platform-appropriate existing resource limits where supported, and record actual enforcement and unsupported limits. Direct mode promises time/output bounds, not bounded host disk or universal cross-platform memory quotas. Keep sandbox Python/Lean address-space and tmpfs policies unchanged. Do not add a dependency solely for resource parity.

Alternative rejected: relaxing `sandbox_runtime.run` until it executes natively. Its seccomp, descriptors, selectors and mount semantics are deeply Linux-specific; a small native recorder avoids spreading conditionals through working isolation code.

### 3. Preserve formal checking, parameterize physical paths

Retain the existing compiler, full `Main.olean`/server/private/IR family, byte and aggregate retention bounds, helper source pinning, primitive profile, safe-declaration restrictions, complete semantic capsule and exact ordered libraries. Keep compilation and verification separate processes. Reuse formal orchestration and binding logic only where it reduces duplication without introducing a framework.

Give the helper an explicit output-path argument; preserve its legacy invocation/output behavior for historical helpers and existing sandbox validation. Native checking supplies platform-native staged roots rather than creating privileged `/toolchain` or `/outputs` directories. Use platform path separators and explicit empty-path removal; clear ambient overrides before loading the pristine reference profile.

For new evidence, record a producer-bound role-to-physical-root descriptor for toolchain, ordered libraries and retained objects. Validate reported native paths against that descriptor and exact manifests, retaining root-relative portable file identities. Root membership is component-based, rejects traversal/redirected paths, respects target path semantics, and does not use string-prefix containment. The role set and root order must match the committed plan/toolchain and the recorder's own staging layout; the verifier report cannot nominate arbitrary trusted roots. Old evidence continues using its exact guest-root rules.

Copy/stage exact reviewed bytes, verify before use and after checking, and collect only bounded regular outputs with redirection checks. Native permissions cannot establish immutable roots against the same account: describe roots as byte-verified staged inputs, not sandbox-enforced immutability. Imported toolchain/library bytes remain manifested rather than copied into canonical state, as today. Full source-to-object correspondence and original-target fidelity remain separate from kernel success.

Alternative rejected: using `leanchecker --fresh` alone for modern receipts. It omits the existing primitive-reference, semantic and retained-resolution evidence.

### 4. Explicit evidence versioning and historical dispatch

Introduce a new execution-envelope/receipt version for newly launched mode-aware runs; retain validation and recovery of `checked-compiled-evidence-v1` with all original namespace, request and resolution checks. Keep the mathematical primitive profile unchanged. Dispatch receipt writers and validators by recorded protocol, not today's default. Update version acceptance in `research.py` and bounded projections in `context.py`; do not turn every non-current legacy receipt into modern evidence.

Separate successful process predicates from backend evidence validation. For direct mode require native producer/environment bindings and explicit `isolation_established: false`; for Bubblewrap retain namespace attestation. Reject absent/unknown protocols, mode mismatches and fabricated isolation. Computation observations retain exit/timeout/output facts without becoming proof; setup failures remain execution failures.

Bind mode/environment/limit metadata to the committed request, recorder result, canonical receipt and evidence manifest. Expose only bounded factual assurance metadata in review packets, preserving omission of arbitrary stdout, other verdicts and source-review identities.

Keep `campaign.py` candidate closure and release logic unchanged unless narrow protocol plumbing proves necessary. Test their existing evidence/review paths in both modes. No candidate re-freeze is required solely because the default changes; changed evidence still requires the existing new binding/freeze/audit process.

Alternative rejected: making namespace fields universally optional, or globally replacing the receipt-version constant. Both silently change historical assurance.

### 5. Native toolchain selection reuses publisher provenance

Map the execution target to official ZIP markers: `windows` for x86-64, `linux`/`linux_aarch64`, and `darwin`/`darwin_aarch64`. Native Lean support is bounded to these pinned-release combinations; unsupported targets fail explicitly while native Python remains usable. Normalize common CPU aliases without emulation fallback. Bubblewrap retains its currently supported Linux target, including Windows/WSL transport.

Reuse publisher asset SHA-256, safe archive extraction, exact full file manifests, fresh unique trees and toolchain IDs. Set executable permissions for required Unix distribution executables after verified extraction; use `lean.exe`/`leanchecker.exe` on Windows. Check target compatibility before launch and verify manifests before and after execution. Do not accept arbitrary PATH Lean binaries or introduce Elan as a mandatory dependency.

### 6. Preserve harness architecture and maintained sources

Keep all existing Codex role names, paired agent formats, model/effort omission, shared mathematical role content and current skill locations. Maintain the existing `.codex/skills` and compatibility `.agents/skills` payloads from the same wrapper source without inventing new mode variants or moving files. Clarify deployment selects the existing appropriate wrapper location; this change makes no new host-discovery claim.

Update only execution-specific assertions in `mathtrace/native.py`, shared protocol/computationalist role/help, and matching managed projections. Remove stale `.planning` runtime/development-navigation references without making campaign skills load OpenSpec. Reflect wrapper-generation consistency in renderer/research/README and focused tests. Before overwriting a targeted Codex payload, compare against known generated content; preserve or report conflicting owner edits. Avoid regenerating unrelated adapters; shared wording changes propagate only where needed for consistency, with recent adapter-format fixes preserved.

Retain disclosure that Codex lacks the qualified Antigravity capture backend. Execution mode never confers transcript qualification, permits root self-review or repairs independent-review provenance.

## Risks / Trade-offs

- [Native code can access host state and journals] -> execute only root-reviewed code, preserve byte checks and exact evidence, explicitly report the local trust boundary; do not describe hashes as hostile-code isolation.
- [Process cleanup differs by OS and escaped descendants] -> platform lifecycle controls, descendant/timeout tests and conservative uncertain state when teardown is unestablished; no invented termination certificate.
- [Large exact Lean trees cost staging time] -> reuse current verified archive/tree components; optimize only within existing byte-manifest guarantees.
- [Platform archive layouts or loader behavior differ] -> exercise official pinned distributions on Windows, Linux and macOS; test executable permissions, spaces/Unicode paths and ambient overrides. Fixture-only tests do not establish native support.
- [History accidentally reclassified by new defaults] -> preserved v1 validators/writers plus stored historical fixtures and interrupted-attempt recovery tests.
- [Generated prompts regress owner changes] -> narrow source updates, equality/preservation checks and conflict reporting; no layout migration or broad renderer redesign.

## Migration Plan

1. Add version-aware readers/writers and historical regression fixtures before switching the default. Preserve original helper artifacts and old request reconstruction.
2. Add direct execution and target-compatible toolchains; expose `execution_mode` through existing JSON operations. Keep optional setup tools explicitly sandbox-only.
3. Update owned instructions and documentation together with the default, including the deliberate change to root sandbox requirements and truthful source-correspondence limits. Synchronize the evidence spec Purpose wording only in the normal approved spec-sync/archive phase.
4. Validate deterministic tests, package identity/assets, all specs and real native platform checks. Retain optional Linux/WSL sandbox regression evidence separately; unavailable hosts are reported as unvalidated, not passed.
5. Rollback uses a runtime that understands both evidence versions with an explicitly selected Bubblewrap mode. A pre-change binary cannot qualify newly introduced receipts and must fail closed rather than downgrade them. Never rewrite ledger history or delete receipts to roll back behavior.
