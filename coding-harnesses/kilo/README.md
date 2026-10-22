# Kilo adapter

Research date: 2026-10-21. Target: Current Kilo CLI/custom-subagent documentation; not legacy extension .kilocodemodes.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md |
| Skills / commands | .kilo/skills/&lt;name&gt;/SKILL.md |
| Custom agents | .kilo/agents/&lt;name&gt;.md (plural agents); description, mode: subagent, permission denials |
| Delegation | Native Task delegation or @math-* selection with the complete exact packet. |

Merge .kilo/skills and .kilo/agents, plus shared AGENTS snippet. No legacy .kilocodemodes or neighboring OpenCode configuration is copied.


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: No pinned model or provider reasoning fields; documented default uses invoking primary model. A documented top-level wildcard denies tool permissions; effective extension/MCP tools and context remain unvalidated. No capture backend.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://kilo.ai/docs/customize/custom-instructions)
- [Official source 2](https://kilo.ai/docs/customize/skills)
- [Official source 3](https://kilo.ai/docs/customize/custom-subagents)
- [Official source 4](https://kilo.ai/docs/customize/agent-permissions)
