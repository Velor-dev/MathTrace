# Pi adapter

Research date: 2026-10-21. Target: earendil-works/pi coding agent with its official examples/extensions/subagent extension explicitly installed; not a built-in core feature.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md |
| Skills / commands | .pi/skills/&lt;name&gt;/SKILL.md; native skill loader |
| Custom agents | Official extension's .pi/agents/&lt;name&gt;.md: YAML name and description, full role prompt as body; eleven specialist definitions. Model/thinking overrides omitted. |
| Delegation | Extension subagent tool: single agent/task, parallel tasks, or chain; agentScope: project enables project definitions, both combines them with user agents. Default user scope excludes project agents. Each invocation launches a separate Pi process; omitted model inherits the dispatching model and thinking level. |

Follow SETUP.md to install/link the official index.ts and agents.ts together from a compatible Pi checkout into the user extension directory. Merge .pi/skills and .pi/agents into the target project and the shared AGENTS snippet once. Pass agentScope: project on MathTrace subagent calls; retain project-agent confirmation. No extension is installed or launched by this packaging task. FALLBACK.md is a superseded pointer, not the active integration.

Pi-specific installation, scope and exact tool binding: [SETUP.md](SETUP.md).


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: Extension required. Empty tools lists become undefined and do not request zero tools; tool-free remains the role policy. Processes retain host bootstrap/project resources and effective tools: separate process is not proven read/context isolation. Parallel output can be truncated; chain previous-output substitution is unsuitable for blind work. No producer-bound capture backend or new workflow presets.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/README.md)
- [Official source 2](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/configuration.md)
- [Official source 3](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md)
- [Official source 4](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/examples/extensions/subagent/README.md)
- [Official source 5](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/examples/extensions/subagent/agents.ts)
- [Official source 6](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/examples/extensions/subagent/index.ts)
