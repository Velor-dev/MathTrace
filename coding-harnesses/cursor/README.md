# Cursor adapter

Research date: 2026-10-21. Target: Cursor Agent with documented skills and custom subagents.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md; no duplicated .cursor/rules policy is needed. |
| Skills / commands | .cursor/skills/&lt;name&gt;/SKILL.md; native skill discovery |
| Custom agents | .cursor/agents/&lt;name&gt;.md; name, description, model: inherit, readonly: true |
| Delegation | Native Task delegation to the selected math-* agent with the exact packet. |

Merge .cursor/skills and .cursor/agents and the shared AGENTS snippet. Keep readonly on worker definitions; root retains normal mediation duties.


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: readonly is weaker than tool-free and does not prove blind context or denial of shell/read access. No documented no-tools field is invented; prompt policy remains essential. No capture backend. model: inherit is documented and retained. Legacy request-based plans without Max can substitute Composer; admin/availability limits can also change the effective model. Exact effort parameter inheritance requires observation.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://cursor.com/docs/context/rules)
- [Official source 2](https://cursor.com/docs/skills)
- [Official source 3](https://cursor.com/docs/subagents)
