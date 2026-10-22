# Mathematical evidence evaluation

The canonical database records exact evidence and policy-relative eligibility. It is not a mathematical truth oracle. Immutable records and events are authoritative; each query evaluates a coherent snapshot. No persistent semantic graph or truth-maintenance cache supplies mathematical authority.

## Proof judgments and grounding

An inference declares its conclusion, AND premises, output assumptions, discharged assumptions, proof artifact, external applications and optional formal receipt. Alternative inferences are OR choices. Every selected premise needs a finite grounded derivation. Repeating a claim through different inference records can be legitimate; repeating an inference on one branch is circular and cannot create support.

An output judgment `Γ ⊢ P` is usable only in an environment containing its declared `Γ`. Its premises are checked under `Γ` together with the assumptions discharged by that inference. The artifact and independent discharge review establish binding, freshness, quantifier rules and the actual logical justification. Assumption IDs and rule labels alone do not prove those facts.

Separately relied-on accepted lemmas and external theorem applications must be explicit dependencies. Internal derivations reproduced in reviewed self-contained evidence can remain inside that evidence. This boundary also applies to counterexamples. Reviewers must reject citations to unexplained accepted facts disguised as self-contained reasoning.

An accepted external application qualifies one exact conditional instantiation: source/version, definitions/domains, substitution, all mapped antecedents and conclusion. It proves neither antecedents nor conclusion. Qualification can precede discovery of antecedent proofs. The constructor copies every mapped claim into the consuming inference's AND premises, and the evaluator independently verifies that inclusion. Each premise needs a current argument in the declared inference/discharge scope. The `hypotheses` application review checks complete, faithful antecedent mapping; support belongs to the consuming inference. An unsupported or unconditionally refuted antecedent cannot disappear through application acceptance. Applications do not carry a competing assumption calculus.

A claim-targeted finding initially blocks statement use conservatively. It is not automatically a claim-falsity judgment. Register an exact `adjudication` with `disposition: scope-classified`, `impact: unconditional-truth`, a self-contained response and author when the challenge concerns unconditional truth while the statement boundary remains intact. Captured nonparty adjudicator checks must cover `finding-scope`, `counterargument`, `scope-classified`, `statement-boundary`, `truth-only-impact`, and `evidence-provenance`; include required prior/evidence challenge checks returned for that exact case. `adjudicate` produces a pinned scope-only resolution/event, preserving the finding's substantive status.

Its statement/producer conditions must remain unchanged and its exact scope witnesses current. New evidence challenges or withdrawal restore the broad hold until explicit recertification. Fresh review can assess retained, non-current report bytes without restoring their provenance. Findings against infrastructure, definitions, assumptions or sources cannot receive this claim-only exception. Every other finding and statement withdrawal remains a gate.

A current truth-only scope certificate does not invalidate a legitimate conditional judgment `A ⊢ P`, but continues to block unconditional `P`. For example, a reviewed contradiction argument can use `A ⊢ P` and an explicit proof of `¬P`, then discharge `A` to establish `¬A`. Its negation proof must itself be reproduced in the artifact or be an explicit separately accepted claim dependency. Neither a scope certificate nor counterexample-validation status is an implicit negation premise.

Conversely, adding an unrelated ambient assumption cannot launder a disputed unconditional proof of `P`. The selected inference's output assumptions distinguish conditional from unconditional use; its discharge list does not make its output conditional. A new unconditional proof of a currently refuted or suspended conclusion cannot be promoted. An already accepted proof remains available for conflict diagnosis after later counterevidence arrives.

## Dependency-bearing refutations

A counterexample contains an exact target, evidence artifact, optional formal negation receipt and distinct external claim dependencies. Each dependency needs unconditional grounding. Dependencies omitted by older records mean self-contained evidence, as before; omission does not authorize unexplained external lemmas. New constructors always write the dependency list.

A refutation cannot rely on its target's unconditional truth. A conditional occurrence inside a legitimate discharged proof is allowed. Rejecting every occurrence of the target would incorrectly exclude ordinary negation proofs by contradiction.

Support and refutation can interact non-monotonically. Evaluating them through mutually recursive queries, or treating recursion as absent counterevidence, can invent support. The evaluator instead uses a finite conservative lower/upper construction.

Let `Φ(X)` be the reviewed refutations whose dependencies have finite positive witnesses when unconditional use of targets refuted by `X` is forbidden. Each refutation additionally forbids unconditional reliance on its own target. Starting with `L = ∅` and `U = all admitted refutations`, evaluate simultaneously:

```
L_next = Φ(U)
U_next = Φ(L)
```

`Φ` is antitone: additional forbidden claims cannot create positive witnesses. The lower set grows, the upper set shrinks, and both remain finite. At the fixed bounds:

- `L` contains currently grounded refutations.
- `U − L` contains unresolved circular counterevidence.
- Targets in `U` cannot supply unconditional positive premises.

Unresolved counterevidence suspends use; it does not establish falsity. Losing all grounding for a refutation removes that refutation's eligibility without fabricating a positive proof. Losing one OR route preserves independent alternatives.

Negative admission uses current audited mathematical evidence at every positive assurance. A credible informal counterexample can expose an incorrectly formalized theorem and therefore veto formal-only promotion. Machine-checked disproof publication separately requires a checked formal negation and formal dependency witnesses.

## Query meaning

`claim_state` exposes diagnostic support, consumer-usable support, certain refutations, unresolved refutations, negative-use blockers, scope, policy and snapshot revision. `conflict` preserves a grounded accepted argument together with known counterevidence; `suspended` preserves unresolved counterevidence. Neither state permits unconditional publication. Conditional use must inspect the actual scoped witness and `use` field rather than treating every diagnostic state as a universal truth judgment.

`derivations` and `eligible_supports` return usable witnesses. `grounded_supports` is diagnostic and can include arguments excluded by negative evidence. Missing support means unsupported, not false. Review counts never decide any of these mathematical judgments.

`disputed` identifies a certified claim-truth hold without treating the finding as an actual refutation. `truth_hold_findings` identifies that qualification. Every positive-use and refutation-dependency bound includes the hold; raw finite grounding remains diagnostic. Candidate freeze requires an actual usable unconditional witness, not diagnostic support alone. Formal checking can investigate either orientation under certified statement scope; positive incorporation retains the separate hold.

## Exact freeze and qualification

A candidate selects one complete proof or refutation witness, including its exact dependency choices, assumptions, definitions, applications, formal plans/receipts/toolchain records and compiled artifacts. The witness is a content-addressed forest: ordered roots and only their reachable nodes. Each node binds the exact inference ID/hash, claim, ambient environment, declared output assumptions and ordered selected child hashes. Repeated subarguments are stored once. Proofs have one target root; disproofs have exactly the counterexample's ordered dependency roots, possibly none for self-contained evidence. The writer and reader reconstruct the same complete manifest and hash. The reader checks the exact target, selected nodes and branch-level inference exclusion; an acyclic node graph alone cannot establish grounding. It never swaps in another proof. The summary proof artifact must also remain current.

`derivations` returns one selected forest per eligible root inference, preserving first eligible child choices rather than enumerating Cartesian products. Counterexample referee packets merge selected dependency forests so common subarguments appear once. The evaluator shares queries only within one unchanged snapshot and includes scope, policy, negative-use vetoes, root diagnostic permission and relevant branch exclusions in its cache key. Cyclic graphs can still require many distinct branch contexts. These derived caches are not canonical truth state.

The current evaluator profile is `scoped-selected-forest-v3`. It is a declared semantic policy profile, not a cryptographic implementation attestation. Candidates frozen under earlier profiles require a new freeze and candidate audit; recursive witnesses are never silently migrated. Historical records remain intact.

Inference, application and counterexample qualification reviews can change while the selected mathematical evidence remains identical. Replacing lost qualification for that same argument does not replace the frozen proof. Candidate audit and publication review witnesses are separately pinned; replacing those witnesses requires explicit re-audit. Fatal findings remain blocking until exact supported adjudication. Changed selected proof evidence requires a new freeze. This distinction avoids both silent proof substitution and unnecessary audit expiry after every temporary hold.

Worker-derived artifacts retain their exact result provenance. Retracting the result or its recorded source evidence invalidates reuse. Background admission rationale is independently reviewable and currentness-critical; it is excluded from blind discovery additions to avoid leaking strategy or verdict narrative.

Contract IDs identify mathematical research contexts, not permission namespaces. Explicit lemma dependencies can cross contracts. Reviewers must establish compatibility of domains, definitions, substitutions and permitted foundations; different IDs alone establish neither compatibility nor incompatibility.
