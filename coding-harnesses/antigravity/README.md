# Antigravity adapter

Research date: 2026-10-21. Target: Google Antigravity CLI; existing ready project build.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | AGENTS.md or GEMINI.md; this payload preserves the existing .agents projection only, without restoring the paused root instruction files. |
| Skills / commands | .agents/skills/&lt;name&gt;/SKILL.md; eight existing skill commands |
| Custom agents | .agents/agents/&lt;name&gt;/agent.md; eleven existing native roles |
| Delegation | invoke_subagent using the existing root-mediated reserve/inspect/admit/capture/recover protocol. |

The .agents directory is copied, not moved. Root installation remains authoritative and untouched. Do not invoke the managed installer against this staging directory. For a separate project use the existing supported installation procedure; merge shared project instructions deliberately. The copy's internal paths assume deployment as project-root .agents and the normal runtime/docs layout.


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: Byte-preserved copy of the ready build. Existing runtime and recorded-input qualification prerequisites still apply; residual platform controls remain callable. No new host run.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://antigravity.google/docs/subagents?tab=cli)
- [Official source 2](https://antigravity.google/docs/skills)
- [Official source 3](https://antigravity.google/docs/rules)
