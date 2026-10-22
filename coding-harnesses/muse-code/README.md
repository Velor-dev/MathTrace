# Muse Code adapter

Research date: 2026-10-21. Target: Meta Muse Code; official dev.meta.ai manual and Meta Models developer documentation (next channel).

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md in a trusted workspace; native loading order checks AGENTS.md before CLAUDE.md, .agents/AGENTS.md and .claude/CLAUDE.md at each directory level. |
| Skills / commands | .agents/skills/&lt;name&gt;/SKILL.md; YAML name/description plus Markdown; /&lt;name&gt; or native read_skill activation. Project skills require workspace trust. |
| Custom agents | Native dynamic subagents confirmed; complete standalone custom-agent schema/location not confirmed in inspected sources. Plugin docs mention reviewed Markdown agents under agents/ but do not establish a deployable project schema. Use shared role prompts through the native dynamic tool; no invented .muse/agents schema. |
| Delegation | Root supplies the selected shared role body and complete exact packet to the installed native subagent tools using their actual schema. Workers share checkout by default; per-child worktree isolation is optional and not read isolation. Children can spawn descendants, which MathTrace's role policy prohibits. |

See SETUP.md. Merge only .agents/skills into the target project's skill directory, resolving existing names without replacing a managed .agents tree. Keep shared role library available and merge existing AGENTS instructions once. Trust the workspace through normal host setup. No plugin installation, settings changes or host launch occurs here.

Native setup, role binding and unsupported features: [SETUP.md](SETUP.md).


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: Dynamic tool parameter names, per-child tool denial, complete custom-agent schema and exact model/effort inheritance remain unconfirmed in the inspected official pages. Do not infer them from Codex or Claude formats. No plugin agent capability declaration is fabricated; the docs distinguish advanced reviewed agent files from unsupported capabilities.agents entries. No capture backend or automatic model/effort override. Compatibility imports can install Claude-style agent declarations while leaving them inactive; reviewed plugin agent paths do not establish a general project schema. Worktree separation does not prove input blindness.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://dev.meta.ai/docs/muse-code/extending)
- [Official source 2](https://dev.meta.ai/docs/muse-code/configuration)
- [Official source 3](https://meta-models.github.io/muse-code-sdk/next/guides/extend/skills/)
- [Official source 4](https://meta-models.github.io/muse-code-sdk/next/guides/plugins/concepts/packages-and-capabilities/)
- [Official source 5](https://meta-models.github.io/muse-code-sdk/next/guides/plugins/concepts/trust-review-and-scopes/)
- [Official source 6](https://meta-models.github.io/muse-code-sdk/next/guides/plugins/concepts/compatibility/)
