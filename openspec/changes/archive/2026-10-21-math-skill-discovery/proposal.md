# Proposal

## Why

The two MathTrace entry-point skills load the execution protocol but do not direct the main agent to the existing skill guide. Reading that guide at entry gives the agent enough context to choose relevant skills during mathematical work while retaining flexible, request-driven orchestration.

## What Changes

- Make `math-intake` and `math-progress` instruct the main agent to read the applicable `help.md` directly alongside `PROTOCOL.md`.
- Apply the guidance in maintained native and shared skill sources, regenerate the managed native projection, and propagate it across every supported coding harness, including the Antigravity snapshot and both Codex skill locations.
- Resolve guide references according to each harness's deployed project layout; shared wrappers continue forwarding to shared definitions where appropriate.
- Preserve existing skill mandates, request boundaries, specialist isolation, and the owner's customized Codex agents/skills structure. Skill selection remains discretionary; reading the guide does not invoke `mathtrace-help` or require a skill sequence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `help-and-discovery`: Require direct guide discovery from intake and progress entry points, with equivalent guidance and resolvable paths across supported harnesses.

## Impact

Affected maintained sources are `mathtrace/native.py` and the two shared skill definitions under `coding-harnesses/shared/skills/`. Generated native skills and the two Antigravity snapshot skills require corresponding updates, with managed integrity metadata reconciled only where necessary. Existing thin harness wrappers provide shared-source propagation; focused tests will verify the full harness inventory and preservation of Codex customizations. No mathematical runtime, evidence format, specialist role, dependency, or release-gate changes are planned.
