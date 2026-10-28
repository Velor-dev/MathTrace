# Design: Streamlined npm Installer UX and Execution Model

## Context

The MathTrace npm package (`npx mathtrace@latest`) installs harness integrations, workspace instructions (`AGENTS.md`), and the local Lean 4 verification runtime into user projects. Currently, `npm/lib/install.cjs` invokes `P.external()` to verify that the chosen coding harness CLI exists in the host machine's PATH (e.g., executing `antigravity --version`), which fails for users using desktop IDEs or alternative commands (such as `agy`). Additionally, the installer provides an optional `--execution-mode bubblewrap` flag and checks WSL/libseccomp via `P.sandbox()`, which can hang the terminal on systems without WSL. Finally, `npm/lib/selection.cjs` displays duplicate parenthetical IDs in the interactive menu (`Devin (devin)`, `Antigravity (antigravity)`), and the workspace contains deprecated `.agents/workflows/` files.

## Goals / Non-Goals

**Goals:**
- **Zero Host CLI Dependencies**: Allow users to install any harness configuration into their workspace without requiring the harness CLI to be installed on their PC.
- **Minimalist Harness Selection**: Format harness options cleanly as `${i + 1}. ${h.name}` without redundant parenthetical names.
- **Direct Execution Default**: Remove the optional sandbox download option and `--execution-mode` flag from the npm package, establishing Direct Execution as the sole runtime mode for npm-installed projects and preventing terminal hangs.
- **Supply-Chain & Execution Safety**: Preserve publisher-verified cryptographic checking for Lean 4 downloads and maintain isolated Python execution (`-I`).
- **Workspace Hygiene & Privacy**: Add `.mathtrace/` to `.gitignore` to prevent any local machine paths from being tracked in git, and clean up deprecated `.agents/workflows/` files.

**Non-Goals:**
- Changing the Python core runtime's internal Bubblewrap support in `mathtrace/sandbox.py` (this change is specific to the npm package installer).
- Altering the Lean 4 compiler download and verification mechanism in `bootstrap.py` (which continues to download and cryptographically verify Lean 4).

## Decisions

### Decision 1: Remove Host CLI Verification (`P.external`)
- **Rationale**: Agents run across diverse environments (desktop apps, custom CLI names like `agy`, remote containers, CI). Probing the host PATH with hardcoded executable names is fragile, risks terminal hangs, and blocks valid workspace setups.
- **Alternative considered**: Expanding the command mapping to support `agy` or checking multiple binaries. *Rejected*: This remains fragile as tooling evolves and does not solve the desktop GUI app scenario. Removing the check entirely is the clean solution.

### Decision 2: Remove Sandbox Mode and Probing from npm Installer
- **Rationale**: The npm installer targets local developer project setups. Direct Execution with pinned Lean 4 is the primary mode. Bubblewrap requires Linux/WSL and apt packages which complicate npm installation and can hang Windows commandline terminals when probing WSL.
- **Implementation**:
  - Remove `--execution-mode` from `npm/lib/selection.cjs` and `npm/bin/install.cjs`.
  - Fix `mode` to `'direct'` in the installer options.
  - Remove `P.sandbox(args.mode, exec)` from `npm/lib/install.cjs`.
  - Remove the Bubblewrap WSL probe from `npm/lib/prerequisites.cjs`.

### Decision 3: Minimalist Harness Menu Formatting
- **Rationale**: Formats like `1. Devin (devin)` or `4. Antigravity (antigravity)` are redundant and visual noise.
- **Implementation**: Change `selection.cjs` to render `${i + 1}. ${h.name}`.

### Decision 4: Workspace Security & Privacy via `.gitignore`
- **Observation**: During installation, `.mathtrace/install.json` records host paths (`basePython`, `project`).
- **Guidance**: Ensure `.gitignore` explicitly includes `.mathtrace/` so local receipt metadata cannot be committed to git.
- **Integrity**: Confirm that `run.cjs` continues using isolated Python (`-I -m mathtrace`) and boundary validation.

### Decision 5: Legacy Workflow Cleanup
- **Rationale**: Workflows under `.agents/workflows/*.md` (`opsx-apply.md`, etc.) are legacy and deprecated; modern skill equivalents are already active in `.agents/skills/openspec-*`.
- **Implementation**: Safely remove `.agents/workflows/` legacy markdown files from the workspace.

## Risks / Trade-offs

- **[Risk] Existing npm unit tests expect `P.external` and `P.sandbox` errors**:
  - *Mitigation*: Update unit tests in `npm/test/prerequisites.test.cjs` and `npm/test/integration.test.cjs` to match the simplified contracts.
- **[Risk] Harness documentation references**:
  - *Mitigation*: Keep `coding-harnesses/<harness>/README.md` and `SETUP.md` intact so users have complete configuration instructions for their chosen agent.
