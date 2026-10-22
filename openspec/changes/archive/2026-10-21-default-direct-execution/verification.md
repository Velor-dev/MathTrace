# Verification evidence

Implementation retains the standard spec-driven change; no archive, commit or publication was performed.

- Full deterministic suite: 333 passed, 1 Unix-only permission check skipped on Windows, 57 subtests passed (88.06 s).
- Native Linux execution tests through available Ubuntu WSL: 12 tests passed with the Windows-specific test skipped. This exercises Linux native processes; WSL is not a runtime dependency for Direct Execution on Windows.
- Optional Bubblewrap computation/seccomp/retained-output tests: 16 passed through existing Windows/Ubuntu WSL transport.
- Package validator: exact 30 runtime/helper assets, installed identity and wheel fidelity passed. Latest evidence: `work/validation/packaging/runtime-a0d226a7b5ab4308b3c24de3c60ae295/wheel-evidence.json`.
- OpenSpec validation: all 12 specs/changes passed.
- Real Windows x86-64 pinned v4.30.0: proof standalone fresh replay, module-proof checked-target replay, canonical receipt qualification/freeze/withdrawal, invalid proof rejection, kernel-bypass rejection, and sorry axiom rejection verified. Retained outputs under `work/validation/direct-execution/`; canonical bookkeeping evidence at `work/validation/formal/canonical-receipt-5a1372aaa2ad44c5aca0004c1b4fe797/evidence.json`. Independent review captures in that utility are synthetic fixtures, not actual reviewer qualification.
- Native input staging and process lifetime records explicitly report no sandbox isolation. The final native helper uses byte-verified-staged-root language; its canonical rerun passed at `work/validation/formal/canonical-receipt-a37c4a8902454850b479531e304f1c17/evidence.json`.
- A retained pre-change canonical receipt rejects with `Retained semantic capsule differs from the terminal bytes` under BOTH its original packaged validator (`runtime-5c43a813d4214ff4b30963a9aa6ecdd7`) and the updated validator. This is preserved pre-existing ineligibility, not a migration repair. Synthetic intact v1 receipt and recovery tests pass.
- Retained Antigravity staging contains pre-existing manifest/content differences. Unrelated content is preserved. Only reviewed execution-related wording and its corresponding manifest entries are changed; no full snapshot replacement was performed.

## Coverage limitations

macOS and AArch64 hosts are unavailable. Their real executable/toolchain behavior remains unvalidated; deterministic target/path tests do not establish live platform support. Real optional WSL Bubblewrap canonical formal checking passed at `work/validation/formal/canonical-receipt-dd289ab3da8941c8a56350e1b0956af2/evidence.json`. Real Linux x86-64 native canonical checking, receipt qualification, candidate freezing and withdrawal passed at `work/validation/formal/canonical-receipt-f08e4d6662ef4ced8f4629d489a16dfd/evidence.json`. The official archive was re-extracted onto Linux local storage with exact manifest equality; the slower Windows-mount preflight was terminated before any execution intent existed. Standalone Linux `leanchecker --fresh` also passed; retained evidence is `work/validation/direct-execution/validation-linux-proof.json`. Native Linux toolchain archive/permission tests passed (5 tests). macOS/AArch64 limitations are explicitly recorded and do not count as live validation.

Final targeted regressions after the historical-protocol guard: 33 passed, 37 subtests passed. All 18 implementation/available-host verification tasks are complete; no unavailable-host pass is claimed.
