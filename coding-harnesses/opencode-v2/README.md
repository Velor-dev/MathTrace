# OpenCode V2 adapter

Research date: 2026-10-21. Target: OpenCode V2 Markdown-agent profile with plural ordered permissions; explicitly separate from V1 and Kilo.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md |
| Skills / commands | .opencode/skills/&lt;name&gt;/SKILL.md; native skill tool/discovery |
| Custom agents | .opencode/agents/&lt;name&gt;.md; filename-derived ID, description, mode: subagent, permissions: [{action: "*", resource: "*", effect: deny}]. |
| Delegation | Native V2 subagent delegation or direct named agent selection using the installed schema and complete exact packet. User selection alone is not evidence capture. |

See SETUP.md. Merge only this V2 .opencode/skills and .opencode/agents into the project, preserving existing configuration and shared AGENTS instructions. Do not deploy the opencode V1 payload alongside this same-name role set. Verify the installed generation and effective permission rules.

Native setup, role binding and unsupported features: [SETUP.md](SETUP.md).


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: V2 uses permissions, shell and subagent instead of V1 permission, bash and task. Catch-all action/resource denial is configured, not live-verified. Effective model/effort and ambient context still require inspection; no pins or automatic routing are added. No capture backend.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://opencode.ai/v2/docs/agents)
- [Official source 2](https://opencode.ai/v2/docs/permissions)
- [Official source 3](https://opencode.ai/v2/docs/skills)
- [Official source 4](https://opencode.ai/v2/docs/instructions)
