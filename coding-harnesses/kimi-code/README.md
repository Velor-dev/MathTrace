# Kimi Code adapter

Research date: 2026-10-21. Target: MoonshotAI/kimi-code current Node CLI Markdown profiles; archived Python kimi-cli is retired from this adapter.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md; preserve existing instructions and generic .agents assets. |
| Skills / commands | .kimi-code/skills/&lt;name&gt;/SKILL.md; user $KIMI_CODE_HOME/skills (default ~/.kimi-code/skills); generic .agents/skills also discovered. |
| Custom agents | .kimi-code/agents/&lt;name&gt;.md with name, description, tools: [], subagents: [] and the unchanged full role body. No legacy YAML agent map or provider model fields. |
| Delegation | Native Agent tool selecting a discovered math-* subagent_type with the complete exact task packet. Use a fresh context and the installed tool schema. |

See SETUP.md. Merge only .kimi-code/skills and .kimi-code/agents into the target project; keep shared references and existing AGENTS instructions. Start a fresh host session and confirm project-root discovery, especially outside a Git checkout. Extra roots use extra_agent_dirs. Installed legacy configuration and external/modified files are preserved.

Native setup, role binding and unsupported features: [SETUP.md](SETUP.md).


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: Without a secondary-model pool/force override, model and thinking inherit. A configured secondary pool changes omission semantics; verify effective settings and do not enable routing. Empty tools/subagents are explicit denials. Project-root discovery and effective context/tool controls require installed-version inspection; unknown foreign model/mode fields are not inheritance controls. No capture backend.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://github.com/MoonshotAI/kimi-code)
- [Official source 2](https://github.com/MoonshotAI/kimi-code/blob/main/docs/en/customization/agents.md)
- [Official source 3](https://github.com/MoonshotAI/kimi-code/blob/main/docs/en/customization/skills.md)
- [Official source 4](https://github.com/MoonshotAI/kimi-code/blob/main/docs/en/reference/kimi-command.md)
- [Official source 5](https://github.com/MoonshotAI/kimi-code/blob/main/packages/agent-core-v2/src/session/subagent/configSection.ts)
- [Official source 6](https://github.com/MoonshotAI/kimi-cli)
