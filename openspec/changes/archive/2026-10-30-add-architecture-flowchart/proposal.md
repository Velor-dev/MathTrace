# Proposal: Add Architecture and Workflow Flowchart to README

## Why

MathTrace coordinates an advanced multi-agent ecosystem—spanning constructive provers, adversarial falsifiers, independent adjudicators, and Lean 4 formal verification—anchored by an immutable append-only ledger. While the system's capabilities are comprehensively detailed in prose, prospective contributors, researchers, and users benefit greatly from an immediate, visually intuitive overview of how these components interact. Adding a native, beautifully styled Mermaid.js flowchart directly in the `README.md` provides cognitive clarity, highlights the system's dialectical tension, and instills immediate confidence in MathTrace's rigorous verification lifecycle.

## What Changes

- Add a prominent, structured **Architecture & Workflow** section to [README.md](../../README.md) right after **Key Capabilities**.
- Embed a GitHub-native Mermaid.js flowchart (`flowchart TD`) illustrating the end-to-end lifecycle:
  1. **Problem Intake & Contract Ledger**: Intake registration, fidelity auditing, and append-only SQLite ledger persistence with SHA-256 digests.
  2. **Dialectical Multi-Agent Frontier**: The dual-track inquiry loop contrasting constructive proof agents (`Scout`, `Prover`, `Computationalist`) against skeptical adversarial agents (`Falsifier`, `Referee`, `Theorem Checker`).
  3. **Formal Verification & Adjudication Gate**: Pinned Lean 4 kernel verification in an isolated execution sandbox, paired with nonparty dispute adjudication for challenges and counterexamples.
  4. **Frozen Candidate & Release Receipt**: Immutable candidate freezing, multi-dimensional auditing, verified release receipts, and asynchronous advisory learning curation.
- Ensure the Mermaid styling is elegant, accessible, and readable across both GitHub dark and light themes without requiring external image assets.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None (pure documentation and visual presentation enhancement; `skip_specs: true` is enabled).

## Impact

- Affects [README.md](../../README.md).
- Zero changes to Python runtime (`mathtrace/`), tests (`tests/`), or command-line interfaces.
- No impact on existing OpenSpec capability specifications or runtime verification invariants.
