# Devin adapter

Research date: 2026-10-21. Target: Cognition Devin CLI local harness; not a claim of equivalent Devin Cloud configuration.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project root AGENTS.md, automatically read unless importing standard rules is disabled by host configuration. |
| Skills / commands | .devin/skills/&lt;name&gt;/SKILL.md; name/description YAML plus Markdown. Compatible .agents/skills and .windsurf/skills are also documented; this payload uses native .devin only. |
| Custom agents | .devin/agents/&lt;name&gt;.md with name/description and allowed-tools: []; full existing mathematical role prompt. Directory AGENT.md layout and .agents/agents are supported alternatives but not duplicated. |
| Delegation | Native run_subagent selects the registered profile; read_subagent retrieves results. Use the live tool schema with the complete exact packet. Foreground/background workers have separate conversation chains; no parent chat history, but codebase context can be shared. |

See SETUP.md. Merge .devin/skills and .devin/agents into the target project; keep shared files and existing AGENTS.md. Install/authenticate the official Devin CLI separately. Do not hand off to Cloud or enable Fusion/Adaptive routing as part of this adapter. No installation or host configuration change is performed here.

Native setup, role binding and unsupported features: [SETUP.md](SETUP.md).


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: Custom agents are experimental. Omitted model uses the host default subagent model, router/admin-selected, not the parent model. Parent-effort inheritance is not confirmed. MathTrace supplies no model pin/router or nesting override; incompatible delegation stays blocked pending manual user configuration. Empty tool allowlist requests no tools but effective enforcement is unvalidated. No capture backend. Shared role bodies are now byte-identical; compatibility must be established by root before dispatch so the inherited-model sentence is applicable, never rewritten to mask the mismatch.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://devin.ai/cli)
- [Official source 2](https://docs.devin.ai/cli)
- [Official source 3](https://docs.devin.ai/cli/subagents)
- [Official source 4](https://docs.devin.ai/cli/extensibility/rules)
- [Official source 5](https://docs.devin.ai/cli/extensibility/skills/overview)
- [Official source 6](https://docs.devin.ai/cli/extensibility/skills/creating-skills)
