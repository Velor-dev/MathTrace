# PrimeAgent adapter

Research date: 2026-10-21. Target: PrimeIntellect-ai/prime-agent; current Rust implementation, not stale Pi-derived layouts or unrelated similarly named products.

Source revision observed: `0e82362747072cdbcf914e6c9ab9742c3bcbe292`.

| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | Project AGENTS.md, confirmed in resource discovery source |
| Skills / commands | .prime/agent/skills/&lt;name&gt;/SKILL.md; Markdown skills |
| Custom agents | No static custom-agent filesystem format confirmed in the inspected current source; shared role prompts provided instead. |
| Delegation | Documented rlm.spawn(...) creates dynamic children via the Python REPL. Root supplies the exact role and packet through the live exposed schema; no guessed arguments or .prime/agents definitions. |

Merge .prime/agent/skills and shared AGENTS snippet; use FALLBACK.md for dynamic role binding or labeled inline exploration when delegation is unavailable.


For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: The audited Rust child host inherits parent model identity and thinking when no override is requested. Effective tools/context and producer-bound admission remain unvalidated; spawn returns an admission handle before completion. Older TypeScript package guides do not describe this tree. No capture backend.

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

- [Official source 1](https://github.com/PrimeIntellect-ai/prime-agent)
- [Official source 2](https://github.com/PrimeIntellect-ai/prime-agent/blob/main/crates/pa-core/src/resources/mod.rs)
- [Official source 3](https://github.com/PrimeIntellect-ai/prime-agent/blob/main/crates/pa-core/src/skills/loader.rs)
- [Official source 4](https://github.com/PrimeIntellect-ai/prime-agent/blob/main/skills/skill-creator/SKILL.md)
- [Official source 5](https://github.com/PrimeIntellect-ai/prime-agent/blob/0e82362747072cdbcf914e6c9ab9742c3bcbe292/crates/pa-daemon/src/rlm_children/host.rs)
