# Hermes Agent adapter

Research date: 2026-10-21. Target: NousResearch Hermes Agent.

Source revision observed: `6932521f258cca074ed206254b329d5b3b982eac`.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md |
| Skills / commands | Default ~/.hermes/skills; this payload uses opt-in skills.external_dirs pointing to coding-harnesses/hermes-agent/skills |
| Custom agents | No static custom-agent filesystem format confirmed; dynamic role prompts provided. |
| Delegation | delegate_task with exact role/packet in its documented goal/context inputs. Children inherit parent toolsets; do not invent a toolsets argument. |

Keep skills here. Merge config.example.yaml into a chosen Hermes profile/user config after setting MATHTRACE_WORKSPACE to an absolute project path; do not copy it as an automatically loaded project config. Alternatively deliberately install the skills under that profile's skills directory. Shared references require the target project as working directory. No home/profile config is modified by this task.


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: Default leaf children inherit parent model/reasoning absent delegation overrides, plus enabled tools and workspace instruction context. Opt-in orchestrators can delegate further when depth allows; MathTrace does not enable this. No model-facing toolsets parameter or static agent discovery is established. GSD-generated agents are not loader evidence. Optional output-schema tolerance does not replace the exact unfenced JSON contract. No capture backend.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)
- [Official source 2](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
- [Official source 3](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation)
- [Official source 4](https://github.com/NousResearch/hermes-agent)
- [Official source 5](https://github.com/NousResearch/hermes-agent/blob/6932521f258cca074ed206254b329d5b3b982eac/tools/delegate_tool_config.py)
