# Proposal

## Why

MathTrace currently requires Linux Bubblewrap, including Ubuntu WSL on Windows, for Python experiments and Lean verification, and cannot execute these operations on macOS. Native execution should make the existing mathematical workflow available across all three operating systems while accurately separating proof validity, process observations and optional isolation evidence.

## What Changes

- **BREAKING**: make `direct` the default execution mode on Windows, Linux and macOS; retain `bubblewrap` as an explicitly selected Linux backend, including its existing Windows/WSL transport. Never silently switch backends.
- Add native Python execution and native pinned Lean provisioning, compilation and checked-target semantic verification, reusing the existing evidence and recovery contracts.
- Bind selected mode, actual environment, process outcomes and supported limits into execution evidence. Direct receipts explicitly report no sandbox isolation; Bubblewrap receipts retain their attestation requirements.
- Preserve historical receipts, interrupted-attempt recovery, compiled semantic checks, independent review, candidate manifests and release gates through version-aware validation.
- Keep the existing Codex TOML/Markdown agents and skill locations. Update only execution-related instructions, obsolete references and generation consistency; preserve specialist independence and model/effort inheritance.
- Update runtime documentation and regression coverage. No new sandbox systems, harness sandbox integration, mathematical workflows, capture backends, npm installer development or unrelated adapter changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli-and-runtime`: one runtime execution-mode selector, native defaults, target-compatible pinned toolchains and mode-independent harness instructions.
- `formal-and-computational-evidence`: optional Bubblewrap isolation, native process evidence, portable checked-target verification and historical evidence compatibility without changing mathematical admission or release policy.

## Impact

Runtime work centers on `mathtrace/evidence.py`, `execution.py`, `sandbox.py`, `sandbox_runtime.py`, `toolchain.py`, `formal.py`, `lean_inspector.lean`, `context.py` and `cli.py`, with a small dispatcher/native recorder as needed. Tests cover direct execution, existing sandbox behavior, archive provenance, recovery, formal qualification and release invariants. Documentation and generation changes affect `mathtrace/native.py`, owned native projections, shared harness sources, the existing Codex payloads, renderer/research bindings and execution validation tools.

Existing all-sandbox requirements in root instructions and the evidence spec deliberately change. Direct execution trusts reviewed local code and the host account; it does not supply Bubblewrap's host-state protection. The pre-existing absence of qualified Codex capture remains disclosed and cannot be bypassed by this change. SQLite schema, mathematical evaluation, nonparty adjudication and the standard OpenSpec `spec-driven` schema remain unchanged.
