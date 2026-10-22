# Requested fulfillment and stopping

MathTrace separates current mathematical sufficiency, requested delivery, and research exhaustion. It never claims exhaustion. Further autonomous exploration becomes optional once the active request's mathematics meets the requested assurance. Delivery and observation of already-started attempts may remain necessary, and new relevant challenges can reopen eligibility.

The original contract's `completion` prose remains immutable. It does not automatically identify required outputs or imply that every claim sharing the contract is required. Legacy contracts are completion-unbound until an explicit mapping is independently qualified.

Create a request with `completion_request`:

```json
{
  "contract": "exact-contract-id",
  "outputs": [
    {
      "target": "exact-target-claim-id",
      "outcomes": ["proof", "disproof"],
      "assurance": "audited-informal",
      "delivery": "audited-result",
      "duties": []
    }
  ],
  "mapping_artifact": "exact-criterion-mapping-artifact-id",
  "author": "root"
}
```

Outputs form a nonempty AND list. Every target belongs to the original contract; disproof cannot enlarge its permitted outcomes. Supported assurances are `audited-informal` and `machine-checked`; delivery is `audited-result` or `released-result`. Additional duties preserve requirements beyond statement fidelity, such as an elementary proof or an explicitly supplied algorithm. A weaker statement or an easy lemma cannot silently replace the requested result.

Dispatch a fidelity-auditor on the draft request for `completion-mapping` and `criteria-coverage`. Its packet includes the original criterion, all target statements and mapping artifact; qualification does not depend on an existing proof. The reviewer must check complete translation, including assurance, delivery and duties. Missing or unsupported assurance remains unresolved. After captured independent coverage, use `activate_completion` with `identifier`, current `expected`, and explicit `reason`.

Revision requires `previous` when creating the new request and the same `supersedes` when activating it. A draft or alias cannot silently replace the active original scope. Drafts remain visible separately and do not negate an already fulfilled active request.

`fulfillment` with `identifier` returns:

- `mathematics_sufficient`: every required output has a genuinely current candidate audit, compatible outcome/assurance, and independently qualified additional duties.
- `contract_fulfilled`: mathematical sufficiency plus all requested delivery.
- `maintenance`: unknown runs or allocations that require collection/inspection, without retry permission.
- `research_exhaustion`: always `not-claimed`.

A current machine-checked candidate can meet a weaker audited-informal request without relabeling or refreezing. The supported formal profile uses pinned same-kernel compiled-target checking; its label does not assert independently implemented checking or source-to-object correspondence. Any stronger requested requirement must remain an explicit additional duty and cannot be waved through by the label.

For a candidate-specific duty, use `completion_evidence` with `request`, `output_index`, `candidate`, `artifact`, `author`, and optional `additional_evidence` exact IDs. Independently assess `completion-duties` as a fidelity-auditor. Machine-checked evidence also requires `formal-environment` and complete compiled meaning views. Reuse current exact proof/audit/checker evidence; this operation requires neither reproof nor gratuitous recompilation.

`record_fulfillment` with `identifier`, `expected`, and stable `request_id` records a historical certificate. `fulfillment_current` checks its exact mapping reviews, selected candidate/manifests, audit witnesses, duty evidence/reviews and requested publication. Live fulfillment may recover through independent candidate B while an A-bound certificate stays stale. New reviews cannot silently replace its pinned witnesses. Exact request replay retrieves the original certificate and reports its currentness separately.

Publication-only withdrawal can make requested released-result delivery false while audited mathematics remains sufficient. Audited-result certificates do not depend on an optional publication. `progress`, `next` and target-scoped `frontier` expose these distinctions and mark further discovery/strategy work optional once the active requested mathematics is sufficient. Unknown attempts remain inspectable after task withdrawal; do not claim they stopped or automatically retry them.

# Retained counterexample reports

A proposed, withdrawn, or provenance-lost counterexample remains an exact allegation until substantive disposition. An unimported negative worker result is likewise retained. It is not automatically a proved negation. `claim_state`, `counterexample_report_condition`, and `finding_effects` expose pending reports separately from ordinary statement-scope findings and raw support/refutation.

Audit currentness/readiness, publication/currentness and requested fulfillment share a finalization gate over actual selected unconditional judgments. Exact statement-boundary aliases share report relevance. Unused claims do not veto a candidate. A conditional child used to discharge assumptions does not become an unconditional judgment merely because its name occurs in the manifest. A qualified disproof is not blocked by its own target-negative orientation, while its positive dependencies still need clearance. Raw evaluation and freezing for investigation retain their existing semantics.

Use existing informed nonparty adjudication for clearance: `adjudication` with `finding`, self-contained `response`, `author`, `disposition: "dismissed"`, and `report_disposition: "invalid"`, `"irrelevant"`, or `"unsubstantiated"`. Required duties include the exact retained witness, domain, negation and scope. Withdrawal, parser repair, formatting/provenance findings, operational disposal or a new proof do not establish mathematical clearance. Independently review the case's complete checks, then call `adjudicate` with its exact ID and current revision.

Clearance depends on its pinned adjudicator witnesses and response remaining eligible. Changed source/qualification or newly proved report dependencies can reopen it. `case current` describes source/response currency; the effective resolution additionally checks its pinned reviews. Retained negative-result disposition does not restore the result's withdrawn producer status.

The profile is `exact-requested-fulfillment-v1`; retained reports use `retained-counterexample-report-v1`. Deterministic fixtures validate these state distinctions with synthetic reviews/checker outputs. They establish neither mathematical truth nor real host independence.
