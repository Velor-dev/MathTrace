# Codex adapter

Research date: 2026-10-15. Target: OpenAI Codex, current documented custom-agent format.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md; preserve existing shared instructions and merge the supplied snippet. |
| Skills / commands | Existing .codex/skills/&lt;name&gt;/SKILL.md wrappers and .agents/skills compatibility wrappers; deploy the location appropriate to the installed host without duplication. |
| Custom agents | .codex/agents/&lt;name&gt;.toml with name, description, developer_instructions paired with companion .codex/agents/&lt;name&gt;.md |
| Delegation | Native subagent spawning to the selected custom agent, using the currently exposed spawn_agent schema and complete exact packet. |

Preserve the existing .codex/skills and .codex/agents structure; .agents/skills is a maintained compatibility payload. Deploy one appropriate wrapper location; do not replace the existing Antigravity .agents directory or its manifest. Name collisions require choosing one active skill wrapper per name. Custom agents are supplied as standalone TOML configurations paired with companion role Markdown files (.codex/agents/*.md).


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: Child sandbox, approvals, MCP and provider settings inherit host policy. Agent files do not establish per-child tool denial; tool-free remains a prompt policy. Model and reasoning fields are omitted. No non-Antigravity capture backend.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://developers.openai.com/codex/guides/agents-md)
- [Official source 2](https://developers.openai.com/codex/skills)
- [Official source 3](https://developers.openai.com/codex/subagents)
