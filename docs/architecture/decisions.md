# MathTrace Architectural Decisions and Audit Records

This document preserves the authoritative historical architectural decisions, sibling audit dispositions, and assurance limits established during MathTrace development.

---

## 1. Governance and Authority

- **Specification and Change Authority**: OpenSpec (`openspec/`) is the sole formal specification and change-management authority for MathTrace.
- **Architectural Primacy**: Architectural decisions and semantic policies are root-reviewed and verified by deterministic regression tests. Subagents or external models serve as critics and inspectors; they do not dictate core mathematical policy.
- **Development Governance**: Root `AGENTS.md` governs coding-agent sessions and operational workflows.

---

## 2. Canonical State and Event Architecture

- **Append-Only Immutable Ledger**: Campaign state is stored in SQLite with strict foreign keys and an append-only event log.
- **State Digests**: SHA-256 state digests certify state consistency and detect any external tampering or out-of-band mutation.
- **Monotonic Derivation**: Current eligibility, frontiers, and obligations are derived projections over verified event sequences; state is never destructively edited in place.

---

## 3. Mathematical Evaluation and Evidence Logic

- **Scoped Support and Refutation**: Mathematical support and refutations are evaluated within strictly bounded inference scopes rather than ambient global state.
- **Selected Witness Forests (`scoped-selected-forest-v3`)**: Inferences share identical verified subarguments and memoize queries with branch exclusions. Cycle rejection is enforced via finite tree grounding and conservative antitone bounds.
- **Conditional Theorem Applications**: Conditional rules must be qualified before proving antecedents; each mapped hypothesis must be grounded explicitly in every consuming inference.
- **Informal vs. Formal Negatives**: An informal counterexample exposes target infidelity and acts as a blocking veto at every assurance tier. Formal verification does not override a credible counterexample.

---

## 4. Formal and Computational Evidence (Lean 4 & Execution Modes)

- **Official Lean Checker Execution**: Pinned official Lean 4 toolchain with `-j2` compilation and pristine primitive-context checked-target replay; standalone checks retain `leanchecker --fresh`. Native execution is the default and reports actual resource limits.
- **Bubblewrap Host Isolation**: Explicitly selected optional Linux execution occurs in a Bubblewrap container (`bwrap`) with unshared namespaces (IPC, network, PID, UTS, user) and read-only host filesystem bindings.
- **Compiled Semantic Inspection**: Retains exact checked binary semantics, primitive-reference and resolution evidence, rejects declaration/type substitutions, and requires independent original-target fidelity. Source-to-object correspondence remains unverified.

---

## 5. Adjudication, Objections, and Findings

- **Independent Nonparty Adjudication**: Objections and findings are adjudicated by nonparty reviews. Scope certification assesses well-formedness and applicability without acting as substantive mathematical validation.
- **No Silent Substitution**: If an audit witness or prerequisite finding changes, derived certificates cannot silently substitute alternatives beneath historic audits.
- **Finding Scopes**: Findings can target specific candidate implementations or entire mathematical claims. Claim-level findings block all derived support until formally resolved or dismissed.

---

## 6. Adaptive Coordination and Work Intents

- **Committed Work Intents**: Execution operations record durable work intent prior to launching processes, preventing unledgered launches or duplicate execution.
- **Idempotent Recovery**: Terminal execution records attributable journal entries; if interrupted, controllers recover outputs without re-executing.
- **Obligation Tracking**: Multi-step mathematical reductions track obligation lineage and explicit repair states.

---

## 7. Native Agent Isolation and Host Limits

- **Tool-Free Specialist Roles**: Mathematical reasoning roles operate with minimal, strictly controlled tool surfaces.
- **Exact Recorded-Input Admission**: Child agent sessions are qualified via attributable terminal input/output recording without recorded tool misuse.
- **Platform Limits & Model Inheritance**: System prompts bootstrap safely with global platform-guide skills without being deemed contamination. Subagents inherit the root model and reasoning effort by default; dispatcher-level hardware prevention and unmonitored context independence are explicitly unprovided.

---

## 8. Candidate Audit, Completion, and Release

- **Candidate Freezing**: Prior to release or publication, candidate artifacts, manifests, and witness sets are frozen.
- **Multi-Dimensional Audits**: Release requires nonparty disposition of all pending counterexample reports, non-empty criteria mapping, and explicit fulfillment verification.
- **No Retroactive Certification**: Historical release receipts remain immutable; revised candidates generate new release chains.

---

## 9. Advisory Learning Boundary

- **Advisory Separation**: Empirical lessons and execution patterns are extracted into an advisory store for worker guidance.
- **Strict Independence**: Advisory items never enter mathematical inference trees, proof certificates, or candidate validation logic as mathematical dependencies.
- **Curation and Revocation**: Advisory lessons are curated against immutable lineage; invalid or obsolete lessons can be revoked without invalidating mathematical theorems.

---

## 10. Native Projection and Help Discovery

- **Managed `.agents/` Projection**: `.agents/math/`, `.agents/agents/`, and `.agents/skills/` are programmatically projected from `mathtrace.native`. External tools (such as OpenSpec skills and workflows) are safely preserved.
- **Guided Discovery**: Interactive discovery via the `/mathtrace-help` skill provides structured access to mathematical commands, workflows, and protocol instructions.
