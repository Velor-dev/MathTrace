# OMP adapter

Research date: 2026-10-21. Target: Oh My Pi: can1357/oh-my-pi. The abbreviation is ambiguous; this payload targets this official repository, not other forks/products..

Source revision observed: `d5cd750e41fede277f9eb933455da92a0738915e`.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md via agents-md context provider; native .omp/AGENTS.md is also supported but not duplicated here. |
| Skills / commands | .omp/skills/&lt;name&gt;/SKILL.md |
| Custom agents | .omp/agents/&lt;name&gt;.md; name, description, tools: [], spawns: [] |
| Delegation | task tool with tasks:[{agent: selected math-* name, task: complete exact packet prompt, solutionSpace: task scope}] and only task-neutral common context. |

Merge .omp/skills and .omp/agents, plus the shared AGENTS snippet. Inspect effective providers/additive tools and selected model settings; do not treat an empty built-in list as enforced universal tool denial.


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: tools: [] disables built-ins, but MCP/extensions/custom tools remain additive and required yield may remain. spawns: [] disables declared child spawning. Host model-role/default configuration can affect selection; no model or effort field is added. No capture backend. Plan mode replaces worker tools with read-oriented capabilities; structured mode can add yield. Neither is zero-tool operation. Omitted thinking alone does not establish equality with the live parent effort; inspect settings and effective resolved controls.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://github.com/can1357/oh-my-pi)
- [Official source 2](https://github.com/can1357/oh-my-pi/blob/main/docs/context-files.md)
- [Official source 3](https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md)
- [Official source 4](https://github.com/can1357/oh-my-pi/blob/main/docs/task-agent-discovery.md)
- [Official source 5](https://github.com/can1357/oh-my-pi/blob/main/docs/tools/task.md)
