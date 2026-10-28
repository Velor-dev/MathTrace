# Proposal

## Why

When users run `npx mathtrace@latest` to install MathTrace into their project, the installer currently extracts an extraneous `coding-harnesses/` directory (containing `shared/`, `catalog.json`, and harness-specific folders) directly into the target project root. This clutters the user's project root with redundant adapter templates and documentation that belong in the installer payload or under `.mathtrace/`.

Furthermore, during the provisioning of the isolated Python virtual environment and the download/unpacking of the Lean 4 verification engine (~100MB), the installer provides no terminal progress feedback. This creates an apparent CLI freeze ("hanging") that degrades developer confidence.

## What Changes

- **Target project root cleanliness**: Prevent `coding-harnesses/` from being created at the target project root during installation.
- **Relocated shared references**: Any shared protocol, policy, or guide references needed by coding harness wrappers are relocated cleanly under `.mathtrace/` (e.g., `.mathtrace/shared/`) or encapsulated within the respective harness directories, leaving the user's project root uncluttered.
- **Terminal progress visibility**: Provide clear, user-friendly console status messages during the long-running bootstrap phases (Python virtual environment initialization, wheel installation, and Lean 4 toolchain downloading/unpacking) so the installer never appears to hang.

## Capabilities

### New Capabilities

*(None)*

### Modified Capabilities

- `project-installation`: Constrain project root deployments so `coding-harnesses/` is never deployed to the target project root, ensure shared references live under `.mathtrace/`, and require visible progress feedback during runtime/toolchain provisioning.

## Impact

- `npm/lib/install.cjs`: Update file mapping logic so `coding-harnesses/shared/`, `coding-harnesses/<harness>/`, and `coding-harnesses/catalog.json` are not mapped to `<root>/coding-harnesses/`. Relocate any required shared files to `.mathtrace/shared/`.
- `npm/bin/install.cjs` / `npm/lib/install.cjs`: Add standard stdout progress indicators during long-running tasks.
- `npm/test/`: Update installer and file mapping tests to verify that `coding-harnesses/` is absent from the target project root after installation.
