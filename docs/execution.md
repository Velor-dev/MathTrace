# Execution intent and recovery

Workers propose exact computation or Lean source. The root reviews scope/source integrity, and for Lean additionally target fidelity and foundations. No worker response executes code automatically.

`run_experiment` and `run_lean` commit an immutable execution intent before calling the selected backend. It binds the exact plan/source/target, request hash, timeout, source reviews, preflight revision/event head and formal checker metadata when applicable. Execution operations refuse an enclosing database transaction: a caller must not be able to roll back the launch intent after starting a process.

For optional Bubblewrap execution, the trusted Linux recorder creates a fresh attempt directory outside every guest mount. It records its request binding, actual process identity and recorder hash before launch, and atomically saves terminal output after recorder-owned guest processes have been waited for. Exception cleanup precedes a terminal certificate. The existing namespaces, read-only inputs, seccomp restrictions and process teardown remain its isolation boundary.

The producer journal is local host evidence, not cryptographic attestation. Its recorded PID/start identity does not establish present liveness. `pending` means committed launch intent; it does not certify observed execution. Transport timeout, missing output and interruption remain uncertain unless an exact attributable terminal observation is available.

Successful synchronous responses preserve the recorder's actual producer descriptor and envelope. They can establish observed completion even if the local spool becomes unavailable; the root never synthesizes producer attribution or teardown from a bare result. In Bubblewrap mode, namespace setup failures are retained as execution-failure receipts. Recovery applies the same evidence classification rather than bypassing the isolation gate.

Use `inspect_execution` with the attempt ID to inspect recorded producer identity and terminal availability. Use `recover_execution` to import retained terminal output without running the program again. A root crash after process completion but before the campaign transaction can therefore recover the same receipt. Duplicate terminal import is idempotent; conflicting output under one attempt ID is rejected. Canonical records/events establish the result association; the general request cache is not authoritative.

Repeating a run operation with the same parameters retrieves the existing attempt's receipt. An uncertain attempt cannot be restarted. A deliberate reproducibility run supplies `rerun_of` naming the latest terminal attempt and a nonempty `reason`; it creates a new immutable attempt. Historical receipts from before this protocol also require an explicit rerun reference. Changed source or formal library environment requires a new reviewed plan.

Completed output is retained even when scope is withdrawn while the process runs. `observed` and `checked` describe recorded process evidence; current mathematical eligibility remains a separate query. A failed computation is not a theorem refutation. New formal execution and recovery preserve exact pinning, archive provenance, staged-byte checks, post-run environment checks, axiom inspection, fresh kernel replay and target-fidelity separation.

Completion observations are immutable terminal events distinct from execution status. Withdrawing an execution or its provenance leaves the recorded output accessible as history, with current attribution explicitly false. Late completion can be recorded for a withdrawn attempt without resurrecting it. Rerun authorization still requires currently attributable terminal evidence.

`next` surfaces nonterminal attempts for inspection and terminal backend failures for root assessment. Plans with prior attempts/receipts are not offered as untouched runnable proposals. No scheduler performs automatic reruns. Missing terminal evidence can require host investigation; this implementation deliberately provides no unsupported “mark stopped” bypass.

Failed Lean checks and computation receipts remain in next-action routing until the root records `assess_execution`, with reasons, exact scoped followups and a reopening condition. Assessment is operational only. Its failure/partial-progress certificate remains in the bounded informed portfolio after retraction; blind workers receive no such history.

Mathematical qualification remains a separate frontier after assessment. Missing plan/receipt checks request the respective review. Withdrawn sources, executions, toolchains or compiled artifacts request repair; a completed review is not a repair of missing provenance. Formal eligibility reports these causes instead of overloading a single non-current Boolean.

A qualified receipt with no active exact mathematical route remains available as `consider-formal-evidence`. Construct a scoped inference/counterexample and obtain its required independent review; qualification alone does not promote it. Proposed references retain their evaluation frontier. Historically accepted but unusable or withdrawn routes do not consume the receipt. Conflict/challenge actions retain their independent gates.

Use `dispose_formal_evidence` with the receipt ID, reason and reopening condition only for deliberate non-use of currently qualified evidence without an active route. Its exact advisory basis includes target state and reference conditions; optional `basis_sources` bind exact additional rationale. The certificate is retained in the informed portfolio. Changed material conditions invalidate applicability. This event neither assesses the process nor accepts/dismisses mathematics, and it cannot suppress receipt review or provenance repair.

## Direct default and explicit optional sandbox

`run_experiment`, `run_lean` and `install_lean` accept one optional JSON argument, `execution_mode`: `direct` (default for new work) or `bubblewrap`. For example:

```json
{"identifier":"experiment-EXACT-ID","timeout":60,"execution_mode":"direct"}
```

Use the existing `python -m mathtrace run_experiment --input request.json` operation. For Lean installation supply `{"version":"v4.30.0"}` to `install_lean`; a formal run supplies its exact `identifier` and `toolchain` IDs. Explicit `bubblewrap` installation targets Linux even on Windows. `python tools/setup_execution.py` provisions only this optional sandbox. Direct execution does not probe WSL or Bubblewrap. Selection failure never changes backend.

Existing attempts recover under their recorded mode when selection is omitted; an explicit conflicting mode fails. Recovery does not rerun code. A deliberate mode-changing rerun must name the latest attributable terminal attempt and give its reason.

Native execution trusts root-reviewed code and the local host account. It has no filesystem/network isolation and cannot protect canonical state or journals from a hostile same-user program. Receipts record `isolation_established: false`; this does not invalidate a successful mathematical check. Python runs through the installed interpreter, with explicit inputs and a controlled environment. No shell executes workload commands.

Native stdout/stderr share a 4 MiB cap and finite wall timeout. Linux/macOS use POSIX sessions/process groups with CPU, core and file-size limits. Linux additionally enforces per-process address-space limits (Python 2 GiB, Lean 8 GiB); macOS reports this limit as not enforced. Escaped descendants are not namespace-contained. Windows uses a Job Object assigned before a trusted gate starts the workload, without claiming sandbox isolation or POSIX memory limits. Aggregate memory and temporary-directory disk quotas are not enforced in direct mode. Actual enforcement is recorded. Unresolved cleanup cannot publish terminal teardown or authorize retry.

New mode-aware formal receipts use `checked-compiled-evidence-v2`; the primitive checking profile is unchanged. Original v1 requests, guest roots and namespace checks remain valid under their original rules. Pre-profile legacy evidence is not upgraded, and old pending attempts retain their original writer. The local journal is producer-bound evidence, not cryptographic host attestation.
