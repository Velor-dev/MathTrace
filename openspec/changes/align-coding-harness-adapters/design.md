# Design

## Context

See proposal.md and the approved report at work/harness-audit-2026-10-21/AUDIT-AND-REMEDIATION.md. The staging renderer is a standalone standard-library script; research.json supplies host bindings. Existing native-agent-isolation requirements continue to govern runtime admission. No third-party host has been qualified here.

## Goals / Non-Goals

**Goals:** expose correct staging paths and dialects, retain exact shared mathematics, document audited limitations and preserve external files through migration.

**Non-Goals:** live host installation/inference, a new capture backend, changing root .agents or shared mathematical semantics, automatic routing, and native integration for unconfirmed dynamic registries.

## Decisions

- Keep `opencode` as the backward-compatible V1 selector and add `opencode-v2` as a separate catalog/research entry and staging directory. Both deploy to `.opencode` but are mutually exclusive. This avoids a silently breaking default or a mutable active variant.
- Add Cline `.yaml` files using frontmatter plus the exact body, `tools: []` and no skills/provider/model fields. Document the pinned source revision and named `subagent_math_*` tool; `.md` discovery is not assumed from GSD.
- Generate current Kimi under `.kimi-code` with Markdown agent bodies, `tools: []`, `subagents: []`. Remove the obsolete root YAML-map emission. Keep secondary-model/configuration caveats root-facing.
- Add an explicit `--migrate-kimi-legacy` renderer option, valid only for all-harness or Kimi selection. A checked-in migration input records exact SHA-256 hashes of the twenty old generated files. Validate every candidate path and content before deleting any; unlink only matching regular files. Never recursively remove directories, follow redirected paths or prune unrelated files. Default rendering does not delete.
- Remove Devin body rewriting; compatibility remains a dispatch prerequisite in transport docs. Retain Claude/Cursor inheritance fields and all other audited native dialects.
- Keep payload generation in render.py. Thin setup guidance is generated there; research.json remains the binding source. Focused regression tests execute the script on isolated staging copies and check output behavior and preservation, not provider inference.

## Risks / Trade-offs

- Upstream source can differ from installed release → qualify source versions in setup and keep host validation explicitly unperformed.
- Legacy modified files block migration → preserve them and report a conflict; never guess ownership from filenames alone.
- Two OpenCode variants share deployment paths → document exclusive selection and test dialect separation/Kilo stability.
- Empty tool lists have different host meanings → retain per-host limitations and unchanged tool-free prompts; no assurance upgrades.

## Migration Plan

Render new payloads; invoke the opt-in staging migration for the verified old Kimi files. Deploy only the selected native directories manually to a target project, preserving user settings. The retired Python target is not retained as an active adapter. Historical source hashes and audit evidence remain available for rollback; a rollback restores old staging files deliberately rather than changing user host configuration.
