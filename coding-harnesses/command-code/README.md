# Command Code adapter

Research date: 2026-10-21. Target: CommandCodeAI/command-code and commandcode.ai; distinct product with its own native agent registry, not Claude Code or the Pi provider.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Root AGENTS.md; .commandcode/AGENTS.md is the documented alternative, used only if root AGENTS.md is absent. Merge shared project instructions once; no CLAUDE.md. |
| Skills / commands | .commandcode/skills/&lt;name&gt;/SKILL.md (this payload); .agents/skills/&lt;name&gt;/SKILL.md also discovered. Native project skills take precedence on name conflicts; /&lt;name&gt; or /skill:&lt;name&gt;. |
| Custom agents | .commandcode/agents/&lt;name&gt;.md: YAML name/description, full role body as system prompt. Omitted tools means none; model and reasoningEffort are omitted. Eleven roles supplied. |
| Delegation | Native agent tool with description, subagent_type: selected math-* name, and prompt: complete exact packet. Multiple calls can run in parallel; background output uses agent_id with agent_output. Children cannot delegate. |

See SETUP.md. Install/authenticate Command Code through its official quickstart (Node.js 22+); merge only .commandcode/skills and .commandcode/agents into the project. Keep shared project paths intact. No Pi extension or Claude configuration is required or copied. Inspect effective agent definitions for personal-name collisions and disclose the documented effort mismatch before delegation. This task installs or launches nothing.

Command Code installation, schemas, discovery and model/effort limits: [SETUP.md](SETUP.md).


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: Documented model inheritance follows the active conversation model, including any host planning/implementation model. Omitted reasoningEffort uses the model default, not documented session-effort inheritance: exact parent-effort preservation is therefore unsupported by this adapter. No automatic compensation/override is added. Personal agents load before project agents and first name wins. Host bootstrap/context/tool behavior is not live-validated; no producer-bound capture backend. Required exact-effort dispatch remains unavailable unless installed-host evidence or explicit manual configuration establishes equality; no reasoningEffort: inherit field is invented.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://commandcode.ai/docs/agents)
- [Official source 2](https://commandcode.ai/docs/skills)
- [Official source 3](https://commandcode.ai/docs/memory)
- [Official source 4](https://commandcode.ai/docs/reference/tools)
- [Official source 5](https://commandcode.ai/docs/quickstart)
- [Official source 6](https://github.com/CommandCodeAI/command-code)
- [Official source 7](https://github.com/CommandCodeAI/command-code/blob/main/readme.md)
