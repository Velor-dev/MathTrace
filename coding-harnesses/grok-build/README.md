# Grok Build adapter

Research date: 2026-10-21. Target: xai-org/grok-build.

Source revision observed: `2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8`.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md; startup rule loading requires folder trust. |
| Skills / commands | .grok/skills/&lt;name&gt;/SKILL.md; skill slash commands (legacy commands are unnecessary) |
| Custom agents | .grok/agents/&lt;name&gt;.md; tools: [], promptMode: full, agentsMd: false |
| Delegation | spawn_subagent selecting the discovered custom subagent_type, with the exact packet in its prompt. |

Merge .grok/skills and .grok/agents; merge the shared AGENTS snippet. Use this product's camelCase agent fields, not another harness's YAML schema.


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: agentsMd: false suppresses project instruction discovery for workers; tools: [] requests no tools. Effective MCP/context and producer attribution are unvalidated here. No model/effort overrides or capture backend. Spawn, role and persona defaults precede parent model/effort fallback. Connected MCP servers inherit by default; inspect effective filtering. Do not substitute cheaper built-ins or resume history for blind tasks.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://github.com/xai-org/grok-build)
- [Official source 2](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-agent/README.md)
- [Official source 3](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/08-skills.md)
- [Official source 4](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/12-project-rules.md)
- [Official source 5](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/16-subagents.md)
