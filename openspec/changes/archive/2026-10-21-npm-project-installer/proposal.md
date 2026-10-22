# Proposal

## Why

MathTrace currently requires separate Python, toolchain, and harness deployment steps that assume access to a source checkout. A small project-local npm installer can assemble the existing runtime and agent assets in one invocation while preserving user ownership and mathematical assurance boundaries.

## What Changes

- Provide `npx mathtrace@latest` with a numbered menu covering every existing harness payload, installing one selected payload into the current project without a global MathTrace installation or separate init command.
- Bundle one verified Python wheel, maintained harness assets, shared dependencies, documentation, and existing rights notices in a version-matched npm payload with no production npm dependencies.
- Require an existing Python 3.11+ with working virtual-environment support; install the wheel into a private project environment and use a persistent project-local runtime launcher.
- Initialize the default campaign store only when absent and provision pinned Lean through existing MathTrace mechanisms. Keep Direct Execution as default and Bubblewrap optional.
- Deploy the complete selected harness dependency closure while preserving customized Codex layouts, user configuration, unrelated skills, and campaign history. Check external harness prerequisites and stop with actionable instructions when missing; make no profile/home/global changes.
- Make reinstall/update ownership-aware, conflict-safe, recoverable, and independent of the source checkout and npm cache.
- Eliminate legacy `gsd_math` wheel contamination using clean builds and complete archive validation; verify the packed npm artifact in standalone projects.
- Preserve current rights-reserved notices without inventing licensing terms. Publication, registry ownership, and any new distribution authorization remain outside this change.

## Capabilities

### New Capabilities

- `project-installation`: One-invocation harness selection, local runtime/toolchain setup, complete asset deployment, safe updates, and truthful installation verification.

### Modified Capabilities

- `cli-and-runtime`: Strengthen isolated wheel build/distribution requirements to reject legacy or unexpected package contents across the complete archive.

## Impact

Adds a small npm entry point and local deployment tooling, release-payload assembly/validation, installer tests, and installation documentation. Reuses `coding-harnesses/research.json`, existing generated assets, `mathtrace.native`, the CLI/store/toolchain APIs, and existing execution backends. Updates `tools/validate_package.py` and packaging tests to verify clean complete artifacts. No new skill, agent role, capture backend, mathematical workflow, model router, automatic Python installer, or release-gate bypass is introduced. No commit or publication is part of implementation acceptance.
