# Cline CLI adapter

Research date: 2026-10-21. Target: Cline CLI configured-agent loader at the audited source revision; verify the installed release.

Source revision observed: `e9dafbb764d0cb9acb4ef93a956ae72c350b3952`.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md is supported; .clinerules/mathtrace.md is an additional supplied root rule wrapper. Merge shared instructions once. |
| Skills / commands | .cline/skills/&lt;name&gt;/SKILL.md; /&lt;name&gt; or use_skill |
| Custom agents | .cline/agents/&lt;name&gt;.yaml: YAML frontmatter plus full Markdown role body; name, description and tools: []. The audited scanner accepts .yaml/.yml, not .md. |
| Delegation | Native named tools such as subagent_math_referee with prompt containing the complete exact exported packet. Profile supplies the unchanged role body; use actual exposed schema. Generic spawn_agent is only a broader compatibility fallback. |

See SETUP.md. Merge .cline/agents and .cline/skills into the target root, preserving external files. Merge shared AGENTS instructions once; retain the supplied .clinerules wrapper as needed. Confirm the installed loader contract before activation; GSD Markdown output does not establish scanner compatibility.

Native setup, role binding and unsupported features: [SETUP.md](SETUP.md).


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: Worker skills, providerId and modelId are omitted. Declaring skills, even [], adds a skills tool. Empty tools remain empty in the audited runtime filter; base runtime model and thinking/effort are inherited. Verify installed-version discovery and effective context/tools/settings before dispatch. Generic Plan/Act subagents have broader tools; prompt restrictions and capture gates remain mandatory. No capture backend.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://docs.cline.bot/customization/cline-rules)
- [Official source 2](https://docs.cline.bot/customization/skills)
- [Official source 3](https://docs.cline.bot/features/subagents)
- [Official source 4](https://docs.cline.bot/getting-started/config)
- [Official source 5](https://github.com/cline/cline/blob/e9dafbb764d0cb9acb4ef93a956ae72c350b3952/sdk/packages/core/src/extensions/tools/team/configured-agent-config.ts)
- [Official source 6](https://github.com/cline/cline/blob/e9dafbb764d0cb9acb4ef93a956ae72c350b3952/sdk/packages/shared/src/storage/paths.ts)
- [Official source 7](https://github.com/cline/cline/blob/e9dafbb764d0cb9acb4ef93a956ae72c350b3952/sdk/packages/core/src/runtime/orchestration/runtime-builder.ts)
- [Official source 8](https://github.com/cline/cline/blob/e9dafbb764d0cb9acb4ef93a956ae72c350b3952/sdk/packages/core/src/extensions/tools/team/configured-agent-tool.ts)
- [Official source 9](https://github.com/cline/cline/blob/e9dafbb764d0cb9acb4ef93a956ae72c350b3952/sdk/packages/core/src/extensions/tools/team/delegated-agent.ts)
