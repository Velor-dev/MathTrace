# Implementation verification

Date: 2026-10-21. All three tracked implementation tasks are complete.

## Delivered

- Cline: eleven `.cline/agents/*.yaml` frontmatter-plus-body profiles with `tools: []`, no worker skills/model/provider fields, and source-qualified discovery/named-tool setup.
- Current Kimi Code: eleven `.kimi-code/agents/*.md` profiles with empty tool/subagent lists and eight native workflows; obsolete Python YAML-map generation removed.
- OpenCode: existing `opencode` V1 selector preserved; separate `opencode-v2` payload uses ordered plural deny rules. Both have explicit exclusive deployment guidance. Kilo retains singular permissions.
- Devin: full shared body identity restored; model incompatibility remains a root-facing dispatch prerequisite.
- All audited binding limitations refreshed; renderer remains the sole payload generator. Historical packaging records explicitly defer to OpenSpec.
- Explicit hash-verified legacy staging migration retired exactly twenty known generated Kimi files. Modified, external and redirected-path preservation is regression-tested; no installed host or user configuration is migrated.

## Checks and results

| Check | Result |
|---|---|
| `uv run --with pytest python -m pytest tests` | **319 passed**, 41.92 seconds; includes six new payload/migration regressions |
| `uv run --with pip python tools/validate_package.py` | Passed; wheel and isolated installed identity match all **27 runtime files** |
| `openspec validate --all` | **11 passed, 0 failed**: ten main specs and this change |
| `openspec validate align-coding-harness-adapters --strict` | Passed |
| Repeated full rendering | Identical file inventory and bytes |
| Selected Cline rendering | Other payloads preserved, including a modified unselected profile |
| Role body comparison | **154** embedded role bodies end with the exact shared source, including JSON contract |
| Protected-file hashes | **139** runtime/root-native/Antigravity-agent/shared input files unchanged |
| Deleted-path comparison | Exactly the **20** entries in the legacy Kimi ownership manifest |

The bare system Python did not have pytest. Verification used uv's isolated pytest/pip dependencies; project runtime dependencies were not changed. Migration was invoked only after all audited legacy hashes matched.

Detailed local evidence is retained in `work/validation/harness-remediation/`: before-hashes.json, payload-check.json, file-changes.json and final-static-check.json. Package evidence is `work/validation/packaging/runtime-5c43a813d4214ff4b30963a9aa6ecdd7/wheel-evidence.json`; wheel SHA-256 is `3d66759d1c1e1adce841f64d2e98f647559b29dff1e949e79c1ff34bc6bbd338`.

## Qualification boundary

No vendor coding host was installed, authenticated or launched. Cline uses the pinned audited loader contract; installed-release compatibility must be checked before activation. Kimi project-root/secondary-model settings and each host's effective tools/context/model/effort remain deployment checks. Configuration and regression success do not provide producer-bound admission or replace independent mathematical gates. Main runtime, root native installation and mathematical sources are unchanged.

The completed change remains available for review and standard OpenSpec archival; no deployment or archival was performed.
