# Claude Code adapter

Research date: 2026-10-21. Target: Anthropic Claude Code with direct AGENTS.md support.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Shared project AGENTS.md directly. Requires v2.1.277+; use a current version (v2.1.285+ for the bundled plugin ID in launch-settings.json). No CLAUDE.md is created. |
| Skills / commands | .claude/skills/&lt;name&gt;/SKILL.md; /&lt;name&gt; |
| Custom agents | .claude/agents/&lt;name&gt;.md; name/description, tools: [], model: inherit, omitClaudeMd: true |
| Delegation | Agent tool with the selected math-* subagent_type and exact packet; use a fresh non-fork worker. |

Merge .claude/skills and .claude/agents. Merge the MathTrace snippet into the project's existing AGENTS.md. Default claude-md-or-agents-md loads AGENTS only if cwd/ancestors lack CLAUDE.md, .claude/CLAUDE.md and CLAUDE.local.md. Optional: launch with claude --settings coding-harnesses/claude-code/launch-settings.json to select claude-md-and-agents-md. The other documented modes are claude-md and managed-only; neither is this adapter's loading choice. Configure via /config, user/managed settings or --settings: project/local settings ignore this pluginConfigs option. Before v2.1.285 the plugin ID is agents-md@builtin. Before v2.1.281 some Bedrock/telemetry-off sessions lack support; disabled plugin or first post-upgrade session can also prevent loading. Update/enable/restart and confirm loading; do not add a redirect CLAUDE.md as a workaround.


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: omitClaudeMd omits user/project/local instructions, including loaded AGENTS.md; managed policy can remain. Environment/git metadata and effective tools still require inspection. No capture backend for this host. model: inherit is supported and intentionally retained; removing it can expose environment defaults. Deliberately empty tool lists are allowed. Invocation/environment/mod overrides can affect model and effort; omit effort to preserve session behavior and inspect effective settings.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://code.claude.com/docs/en/memory)
- [Official source 2](https://code.claude.com/docs/en/skills)
- [Official source 3](https://code.claude.com/docs/en/sub-agents)
- [Official source 4](https://code.claude.com/docs/en/errors#agent-would-be-spawned-with-zero-tools)
