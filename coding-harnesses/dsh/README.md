# DSH adapter

Research date: 2026-10-21. Target: DeepSeek Harness: deepseek-ai/deepseek-harness (developer preview); abbreviation also names unrelated shells/distributions.

Source revision observed: `687f282e8625c6b8d11ff58211a90524be2e4317`.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md via agent-instructions plugin in dsh-base; profiles may change plugin availability. |
| Skills / commands | .dsh/skills/&lt;name&gt;/SKILL.md via skill-filesystem plugin |
| Custom agents | No universal static role-agent file format confirmed; subagent providers and agentPreset are profile/plugin composition. |
| Delegation | Native subagent tool configured for the documented spawn provider (subagent-spawn-in-process) with the complete role/packet. Fresh spawn inherits provider/model/effort by default; fork seeds history and is unsuitable for blind tasks. Use actual exposed schema. |

Merge .dsh/skills and shared AGENTS snippet. Use FALLBACK.md. This targets the official master branch; a missing main-branch document is not evidence of absent support.


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: Requires the instruction/skill/subagent plugins and an inspected provider/preset composition. The preset registry does not scan role directories. Spawn inherits provider/model/reasoning unless agentOptions override them; parent agent-local tool restrictions are not imported automatically. No zero-tool preset bundle or capture backend is supplied.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://github.com/deepseek-ai/deepseek-harness)
- [Official source 2](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/context/agent-instructions/README.md)
- [Official source 3](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md)
- [Official source 4](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/subagent/tool-subagent/README.md)
- [Official source 5](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/subagent/subagent-spawn-in-process/README.md)
- [Official source 6](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/preset/agent-preset-registry/README.md)
