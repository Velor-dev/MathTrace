# Proposal: Simplify npm Installer Experience and Remove Sandbox Option

## Why

When users bootstrap MathTrace in their project using `npx mathtrace@latest`, the installer currently runs invasive host environment probes that check whether the chosen coding harness CLI exists in the system `PATH` (such as checking `antigravity --version`). On systems where tools differ (e.g. `agy` vs `antigravity`) or where desktop GUI applications are used, this causes failures or commandline hangs. Furthermore, probing WSL/Bubblewrap can stall interactive terminal sessions. The harness selection menu also clutters choices by displaying redundant duplicate parenthetical IDs (`Devin (devin)`), and the project contains deprecated `.agents/workflows/*.md` legacy files alongside unignored local runtime metadata.

Streamlining the installer by eliminating host CLI checks and optional sandbox downloading, cleaning up legacy workflows, adding `.mathtrace/` to `.gitignore`, and making the harness selection minimalist directly improves reliability, privacy, and UX for agentic engineers.

## What Changes

- **Remove Host Harness Presence Checks**: Remove external binary execution checks (such as `antigravity --version`, `devin --version`, etc.) from the npm installer so that projects can be provisioned cleanly regardless of whether the harness CLI is installed in PATH.
- **Remove Optional Sandbox Download Option from npm Package**: Remove the `--execution-mode` / Bubblewrap sandbox download options and WSL/Bubblewrap prerequisite checks from the npm installer package, keeping Lean 4 formal engine provisioning via Direct Execution and preventing terminal hangs.
- **Minimalist Harness Selection Menu**: Clean up the interactive harness selection list to display concise, unrepeated harness labels without redundant duplicate identifiers in parentheses (e.g. `1. Devin` instead of `1. Devin (devin)`).
- **Security & Git Hygiene**: Add `.mathtrace/` to `.gitignore` so local deployment receipts (`install.json`, `runtime/`) containing local host paths cannot be accidentally committed to source control.
- **Legacy Workflow Cleanup**: Safely remove deprecated `.agents/workflows/*.md` files (`opsx-*.md`) whose functionality is now handled by modern `.agents/skills/openspec-*` skills.

## Capabilities

### Modified Capabilities
- `project-installation`: Remove host harness executable verification requirements from the npm installer, eliminate the optional Bubblewrap sandbox mode from the npm installer package in favor of standard Direct Execution, and streamline the interactive harness selection interface.

## Impact

- `npm/lib/selection.cjs`: Menu formatting updated to eliminate duplicate parenthetical names; `--execution-mode` flag removed.
- `npm/lib/install.cjs`: Remove `P.sandbox` and host harness CLI presence checks (`P.external`) from the npm installation pipeline.
- `npm/lib/prerequisites.cjs`: Deprecate or remove `commands` CLI probing table and sandbox execution probe for npm installation.
- `npm/bin/install.cjs`: Remove `--execution-mode` from CLI help and options.
- `npm/test/*`: Update selection and prerequisite tests to match the streamlined contract.
- `.gitignore`: Add `.mathtrace/` entry.
- `.agents/workflows/`: Remove obsolete legacy workflow files.
- Existing Python runtime and core verification engines in `mathtrace/` remain unchanged; only the npm distribution package is simplified.
