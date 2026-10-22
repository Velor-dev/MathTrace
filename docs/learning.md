# Local advisory learning

The implemented pipeline is extraction → root curation → explicit informed target admission. Workers cannot curate themselves or supply proof authority.

`advisory_boundary` takes exact revision, event_hash and target. Meaningful boundaries include research decisions, checkpoint registration, native completion, execution terminal/assessment, failure assessments, formal deferral and finding/report disposition. Constructors/readers validate event address/digest, subject kind, typed payload and outcome references. Historical authenticity is distinct from current eligibility.

`extract_learning` takes target, boundary, proposed summary, sources, category, applicability, reopen_condition, author, expected and request_id. It carries the addressed subject and actual outcome/receipt/observation/review references automatically; extra sources must be exact IDs. Checkpoints preserve immutable snapshot identity. An execution ID alone does not select an outcome. Unchanged exact description/basis recovers the same extraction across unrelated revisions; request replay preserves history/currentness after evidence changes.

`curate_learning` takes candidate, reason, author, expected and request_id. Explicit disposition is curate or decline; root can revise summary/applicability/reopen_condition during curation. Curation requires unchanged evidence, while stale proposals can be declined. The candidate's status transition remains lineage, avoiding a self-invalidating source dependency. Advice captures the final typed basis after that transition.

`admit_learning` takes learning, exact target, applicability, reason, author, expected and request_id. Manual/legacy lessons also require this step before automatic selection. Advice curated for another target needs a deliberate new scoped lesson. `select_learning` returns at most max_items current lessons (default8, maximum32), lesson/admission identities and omitted-current/excluded-stale counts.

Only informed strategists receive the selection automatically. Packets include source identities, marked long-text/basis omissions and advisory limits. Blind workers receive none automatically; explicit informed background still uses existing context gates. Revoked admission removes new selection and prevents silent carry-forward in an extension. Old packets remain historical. Admission/source changes stale strategy work without tying it to unrelated revisions.

The curation profile is `source-bound-local-curation-v1`. Fixtures cover authentic boundaries/outcomes, immediate curation currentness, replay, source changes, target scope, omissions, blind exclusion and withdrawal. Reviews/checker outputs are synthetic bookkeeping, not mathematical or host assurance.

Completion boundaries additionally reconstruct the completed run/task at the addressed event and bind the exact packet, response, receipt and captured/reported qualification. Later withdrawal does not erase historical authenticity. A curated origin cannot silently recapture changed evidence under an old candidate; its immutable original basis remains pinned. The candidate itself stays lineage after curation, so withdrawing a proposal does not silently withdraw its separately curated advice. Withdraw the lesson or admission explicitly when that is the intended action. Extra advisory sources may cross scope under root-reviewed applicability; they create no implicit mathematical dependency or equivalence.

`learning` preserves a curated observation with exact sources, a category and a reopening condition. It never supplies an accepted claim or inference. Correctness-critical lessons must become explicit task obligations and independently assessed mathematical evidence.

Currentness means the recorded evidence basis is unchanged and the advice itself is admissible. A failed or unsupported source may support a useful failure lesson. Source-specific snapshots record scope/provenance, qualification causes, scoped grounding, counterexample dependencies, exact candidate witnesses, audit responsibilities, publication witnesses and reviewed finding dispositions. They omit unrelated revisions and interchangeable ordinary positive-review identities. Candidate audit and publication witness selection remains exact.

Two ineligible sources can have different conditions: missing fidelity review, withdrawn toolchain, and retracted compilation output must not collapse into one `False` value. Native review exposure and adjudication witness loss also change the basis even when the source's stored status is unchanged. A fatal finding against the learning itself suspends admission independently of its source snapshot.

A claim-state observation does not select every positive OR alternative. Cite an inference or candidate when the lesson depends on a particular argument. Sources from generated artifacts include their result/run provenance conditions. All source data remains canonical; the condition map is a historical advisory projection, not another authority or truth-maintenance database.

Task creation and extension admit current advice only in informed contexts and mark its advisory status. Extending a task rechecks carried advice as well as newly added records. Old packets remain exact historical inputs; their annotation records the compilation snapshot and does not certify perpetual currentness. An explicit stale-history admission mode has not been implemented. Blind workers cannot receive curated learning/history.

The snapshot profile is `typed-advisory-basis-v2`. Existing status-only learnings become stale and must be recaptured with their exact evidence; no migration invents facts about the historical basis.
