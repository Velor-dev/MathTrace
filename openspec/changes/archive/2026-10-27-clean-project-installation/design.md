# Design

## Context

The MathTrace installer (`npx mathtrace@latest`) currently copies `coding-harnesses/shared/`, `coding-harnesses/<harness>/`, and `coding-harnesses/catalog.json` directly into the root directory of target projects (`<target>/coding-harnesses/`). In projects configuring a specific harness (such as Antigravity, which deploys self-contained `.agents/`), this produces unwanted root directory clutter and duplicates documentation.

In addition, during interactive installation, `npm/lib/install.cjs` executes Python virtual environment creation, pip installation of the MathTrace wheel, and downloading/unpacking of the Lean 4 toolchain without emitting progress feedback to the console, leading users to believe the process has frozen.

## Goals / Non-Goals

**Goals:**
- Eliminate the creation of `coding-harnesses/` in the target project root.
- Relocate necessary shared protocols, guides, and policy references cleanly under `.mathtrace/shared/` (or encapsulate them inside the harness's configuration).
- Keep target project roots minimal: only the selected harness folder (e.g. `.agents/`), `AGENTS.md`, `.math/` (Lean engine & campaign DB), and `.mathtrace/` (isolated runtime).
- Provide clear, user-facing progress messages during runtime setup and Lean 4 toolchain provisioning so the terminal never appears stalled.

**Non-Goals:**
- Removing or altering the native Antigravity `.agents/` projection or specialist roles.
- Changing the Lean 4 version (pinned to v4.30.0) or altering formal verification rules.
- Changing runtime CLI commands or ledger schemas.

## Decisions

### Decision 1: Relocate and suppress root `coding-harnesses/`
In `npm/lib/install.cjs`:
- The file destination mapping in `mapping()` will no longer map any file to `coding-harnesses/...` at the project root.
- Shared assets that need to be accessible within the project (e.g. `shared/POLICY.md`, `shared/PROTOCOL.md`, `shared/help.md`) will be mapped under `.mathtrace/shared/`.
- Harness-specific instructions (`coding-harnesses/README.md`) will be placed inside `.mathtrace/README.md` or `.mathtrace/docs/README.md`.
- In `bind()`, markdown links referencing `coding-harnesses/shared/` will be adjusted to point to `.mathtrace/shared/`.
- For Antigravity, `.agents/` is already self-contained (referencing `.agents/math/PROTOCOL.md` and `.agents/math/help.md`).

*Alternatives considered:*
- Leaving `coding-harnesses/` at project root: Rejected because it pollutes user project roots with non-project files.
- Completely omitting shared files: Rejected because other harnesses (such as Claude Code or Cursor) use thin wrappers that reference shared protocols. Relocating them to `.mathtrace/shared/` satisfies both clean roots and harness requirements.

### Decision 2: Console progress feedback during bootstrap
In `npm/lib/install.cjs` and `npm/bin/install.cjs`:
- Introduce informative console status lines before each long-running step when running interactively:
  - `→ Creating isolated Python environment (.mathtrace/runtime)...`
  - `→ Installing MathTrace package...`
  - `→ Provisioning Lean 4 verification engine (v4.30.0)...`
  - `→ Initializing campaign ledger (.math/state.sqlite)...`
- When `--json` or non-interactive flag is specified, progress output is directed to stderr or suppressed so stdout contains only clean JSON.

*Alternatives considered:*
- Fancy spinner library (e.g., ora): Rejected because MathTrace installer is dependency-free (zero npm dependencies). Simple console status lines with UTF-8 symbols work reliably across all terminals without external packages.

## Risks / Trade-offs

- **[Risk]** Existing tests in `npm/test/` assert the presence of `coding-harnesses/` in target project roots.  
  → *Mitigation:* Update `npm/test/` to assert that `coding-harnesses/` is absent from the project root and verify that all necessary assets resolve in `.mathtrace/shared/`.
- **[Risk]** Interrupted updates from prior versions that already have `coding-harnesses/`.  
  → *Mitigation:* The installer's ownership-aware update journal (`files.cjs`) tracks owned files. When upgrading from v0.1.1, unchanged previously owned files under `coding-harnesses/` will be cleanly retired according to existing ownership rules.
