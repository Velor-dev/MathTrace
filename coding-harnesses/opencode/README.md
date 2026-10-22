# OpenCode V1 adapter

Research date: 2026-10-21. Target: OpenCode V1 Markdown-agent profile with singular permission; use opencode-v2 for the incompatible V2 dialect.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md |
| Skills / commands | .opencode/skills/&lt;name&gt;/SKILL.md; native skill tool/discovery |
| Custom agents | .opencode/agents/&lt;name&gt;.md; description, mode: subagent, permission wildcard deny |
| Delegation | Task delegation or @math-* selection with the exact packet; explicit user selection alone is not evidence capture. |

See SETUP.md. Merge only this V1 .opencode/skills and .opencode/agents into the project, preserving configuration and shared AGENTS instructions. Do not merge opencode-v2 into the same discovery directory. Verify the installed generation before dispatch.

Native setup, role binding and unsupported features: [SETUP.md](SETUP.md).


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: Permission denial is configured, not live-verified; ambient instructions/context still need inspection. Native commands exist in .opencode/commands, but no duplicate command set is added. No capture backend.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://opencode.ai/docs/rules/)
- [Official source 2](https://opencode.ai/docs/skills/)
- [Official source 3](https://opencode.ai/docs/agents/)
- [Official source 4](https://opencode.ai/docs/permissions/)
- [Official source 5](https://opencode.ai/docs/commands/)
