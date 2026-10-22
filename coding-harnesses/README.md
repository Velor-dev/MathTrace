# MathTrace coding harness adapters

Documentation/configuration payloads audited on **2026-10-21**: seventeen products with separate OpenCode V1/V2 variants (eighteen staging payloads). These preserve the current **eight skills and eleven specialist roles**. They add no mathematical phases, commands, fixed sequence, model routing or automatic roster dispatch. Use the existing [skill guide](shared/help.md) to choose the appropriate skill.

The root `.agents/` installation and [Antigravity snapshot](antigravity/.agents/) are preserved. Development is governed by root `AGENTS.md` and OpenSpec. The approved remediation is recorded in `openspec/changes/align-coding-harness-adapters/`; PLAN.md and historical STATUS.md entries describe earlier work, not an alternative planning authority.

## Directory map

```text
coding-harnesses/
  README.md                  entry point, deployment and support matrix
  PLAN.md / STATUS.md        scoped specification, completion and evidence limits
  research.json / SOURCES.md official findings, identities, dates and links
  ORIGIN.json / catalog.json source identities; eight skills and eleven roles
  render.py                  deterministic staging renderer, local writes only
  legacy-kimi-files.json      exact owned hashes for opt-in staging migration
  shared/
    POLICY.md                transport binding and unchanged assurance limits
    project-instructions.md  one shared section to merge into project AGENTS.md
    PROTOCOL.md / help.md     existing protocol and help snapshots
    skills/*/SKILL.md         existing skill bodies with shared reference paths
    roles/math-*.md           complete existing worker prompts
  antigravity/.agents/       exact ready native projection copy
  codex/                     .agents/skills + .codex/agents/*.{toml,md}
  command-code/              .commandcode/{skills,agents} + SETUP.md
  devin/                     .devin/{skills,agents} + SETUP.md
  muse-code/                 .agents/skills + SETUP.md (dynamic role binding)
  claude-code/               .claude/{skills,agents} + launch-settings.json
  grok-build/                .grok/{skills,agents}
  cursor/                    .cursor/{skills,agents}
  opencode/                  V1 .opencode/{skills,agents} + SETUP.md
  opencode-v2/               exclusive V2 .opencode/{skills,agents} + SETUP.md
  pi/                        .pi/{skills,agents} + SETUP.md (official extension)
  omp/                       .omp/{skills,agents}
  primeagent/                .prime/agent/skills + FALLBACK.md
  cline-cli/                 .clinerules + .cline/{skills,agents/*.yaml} + SETUP.md
  kilo/                      .kilo/{skills,agents}
  kimi-code/                 .kimi-code/{skills,agents/*.md} + SETUP.md
  dsh/                       .dsh/skills + FALLBACK.md
  hermes-agent/              skills + config.example.yaml + FALLBACK.md
```

Each harness has its own README with source links, exact native locations, deployment requirements and limitations. Dot directories above are staging payloads; their nesting under this directory does not install them in the current project.

## Supported surface

| Harness | Native skills | Specialist binding | Important limit |
|---|---|---|---|
| [Antigravity](antigravity/README.md) | `.agents/skills` | Existing eleven native agents; `invoke_subagent` | Original bounded capture prerequisites still apply |
| [Codex](codex/README.md) | `.agents/skills` | `.codex/agents/*.{toml,md}`; native spawn | No per-agent enforced tool denial supplied |
| [Command Code](command-code/README.md) | `.commandcode/skills`; compatible `.agents/skills` discovery | `.commandcode/agents/*.md`; native `agent` | Model inherits; omitted effort uses model default, not documented parent-effort inheritance |
| [Devin](devin/README.md) | `.devin/skills` | `.devin/agents/*.md`; `run_subagent` / `read_subagent` | Custom-agent default model is router/admin-selected; parent effort unconfirmed |
| [Muse Code](muse-code/README.md) | `.agents/skills` in a trusted project | Native dynamic delegation with shared role prompts | Complete static agent schema and exact child model/effort inheritance unconfirmed |
| [Claude Code](claude-code/README.md) | `.claude/skills` | `.claude/agents/*.md`; `Agent` | Direct `AGENTS.md` depends on version/loading mode |
| [Grok Build](grok-build/README.md) | `.grok/skills` | `.grok/agents/*.md`; `spawn_subagent` | Empty tools/project-input suppression require effective-context inspection |
| [Cursor](cursor/README.md) | `.cursor/skills` | `.cursor/agents/*.md`; native Task | Read-only is weaker than tool-free |
| [OpenCode V1](opencode/README.md) | `.opencode/skills` | `.opencode/agents/*.md`; Task | Singular `permission`; deploy exclusively from V2 |
| [OpenCode V2](opencode-v2/README.md) | `.opencode/skills` | `.opencode/agents/*.md`; native subagent | Plural ordered `permissions`; deploy exclusively from V1 |
| [Pi](pi/README.md) | `.pi/skills` | Official extension; `.pi/agents/*.md`; `subagent` | Requires extension installation and `agentScope: "project"`; no core subagents |
| [OMP](omp/README.md) | `.omp/skills` | `.omp/agents/*.md`; `task` | Chosen identity: Oh My Pi; additive tools can remain |
| [PrimeAgent](primeagent/README.md) | `.prime/agent/skills` | Dynamic `rlm.spawn` role prompts | Chosen identity: Prime Intellect; static agents unconfirmed |
| [Cline CLI](cline-cli/README.md) | `.cline/skills` | `.cline/agents/*.yaml`; named `subagent_math_*` tools | Version-specific scanner; worker `skills` must be omitted |
| [Kilo](kilo/README.md) | `.kilo/skills` | `.kilo/agents/*.md`; Task | Current CLI format; exclude legacy mode schema |
| [Kimi Code](kimi-code/README.md) | `.kimi-code/skills` | `.kimi-code/agents/*.md`; `Agent` | Current Node product; verify project discovery and secondary-model settings |
| [DSH](dsh/README.md) | `.dsh/skills` | Dynamic `subagent`, profile-dependent | Chosen identity: DeepSeek Harness; static format unconfirmed |
| [Hermes Agent](hermes-agent/README.md) | Profile skills/external directory | Dynamic `delegate_task` role prompts | Opt-in skill source; inherited child tools; static agents unconfirmed |

All non-Antigravity ports and version variants are **instruction/configuration adapters**, without a new producer-bound capture backend. Their worker output is exploratory or operator-reported evidence; it cannot satisfy independent-review eligibility merely by being returned from a native subagent. Existing audit/release/fulfillment gates stay intact. The assigned tool-free worker policy is preserved, but effective enforcement varies and has not been live-tested here. See [POLICY](shared/POLICY.md).

Command Code is a separate product and payload. Its [setup guide](command-code/SETUP.md) records the documented effort-default mismatch, native agent/skill schemas and project discovery. It shares no configuration directory with Claude Code or Pi; Pi continues to target its official subagent extension independently.

## Deployment

The project-local installer and its read-only external prerequisite checks are
documented in [installation](../docs/installation.md). Missing host prerequisites
stop installation; it never changes home/profile settings or installs extensions.

1. Keep this directory at `<project>/coding-harnesses/` and make the existing MathTrace runtime available through its normal supported installation. This directory does not vendor or install the Python runtime, checker or execution environment.
2. Read the chosen harness README and [POLICY](shared/POLICY.md). Merge only that harness's native dot directories/files into the **target project root**. Preserve existing files, project instructions and configuration; resolve name collisions deliberately. Do not copy every harness into active discovery. Hermes uses a profile configuration entry rather than an assumed project-local skill loader; Kimi Code uses current Markdown discovery; OpenCode V1 and V2 must never be merged into the same active directory.
3. Where the harness supports root `AGENTS.md`, merge [project-instructions.md](shared/project-instructions.md) into that one shared instruction file. Do not overwrite repository governance or copy paused `work/` files back. Cline has a native rule wrapper. Claude uses shared `AGENTS.md` directly and ships **no `CLAUDE.md`**; its optional launch settings select the documented combined loading mode without duplicating instructions.
4. Launch the host from the target project root after intentional deployment. The wrappers explicitly read project-root shared paths; they do not depend on universal `@import` handling. Fresh workers receive embedded full role prompts, or the root supplies the full prompt for dynamic delegation. Workers never need to read shared files.

Do not launch a host from these nested staging directories: ancestor discovery may load the current root Antigravity skills or duplicate names. Do not overwrite the managed root `.agents` projection with Codex wrappers or run the native installer on this staging tree. Antigravity's preserved copy retains its original manifest and paths; its duplicate protocol/roles are intentional because the user requested preservation of the ready version.

## Ownership and maintenance

[Shared skills](shared/skills/), [role prompts](shared/roles/), [protocol](shared/PROTOCOL.md) and [help](shared/help.md) own the copied workflow meaning; [POLICY](shared/POLICY.md) owns only the host transport scope. `research.json` owns harness findings and binding descriptions. `render.py` emits thin skill wrappers, format-specific role files and harness READMEs from those inputs. It only writes inside this directory and never installs. Default rendering never deletes; explicit `--migrate-kimi-legacy` retires only hash-matching known old staging files after preflight, preserving modified and external assets. Antigravity is an untouched snapshot and excluded from rendering.

For later regeneration, run `python coding-harnesses/render.py` after reviewing intentional changes to the inputs. Generated wrapper/role edits would be overwritten. Refresh snapshots deliberately from the authoritative runtime renderer when its meaning changes; do not treat these copies as a new authority for the main runtime or reinstall them over its owned projection.

Use `python coding-harnesses/render.py --harness pi` for Pi-only payload regeneration plus the shared source index. The [Pi setup guide](pi/SETUP.md) targets the official extension explicitly and explains inherited model/thinking settings, parallel/chain support and the empty-tool-list limitation. The older Pi FALLBACK file is a superseded pointer.

The original protocol includes Antigravity-specific calls; on other hosts apply the explicit transport binding in POLICY rather than blindly invoking those calls. Shared help keeps existing command names; native invocation/discovery syntax is described per harness. Nothing here claims live host/model qualification or changes mathematical assurance.

See [STATUS](STATUS.md) for current and historical evidence, [official sources](SOURCES.md) and the [approved audit](../work/harness-audit-2026-10-21/AUDIT-AND-REMEDIATION.md). Regression/package/OpenSpec verification is recorded in the change; native hosts have not been installed or qualified.

To retire verified old Kimi staging files, run `python coding-harnesses/render.py --harness kimi-code --migrate-kimi-legacy`. Conflicts abort before deletion; installed user settings are outside its scope. See [Kimi setup](kimi-code/SETUP.md) and the mutually exclusive [OpenCode V1](opencode/SETUP.md) / [V2](opencode-v2/SETUP.md) setup guides.
