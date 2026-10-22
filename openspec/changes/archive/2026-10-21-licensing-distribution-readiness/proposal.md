# Proposal

## Why

MathTrace's existing confidential, research-and-demonstration-only notices contradict the owner's intended free personal, academic, and commercial use. A canonical proprietary license and consistent distribution metadata are needed before public GitHub/npm availability, while publication remains explicitly disabled.

## What Changes

- Establish one canonical `LICENSE` granting no-charge use and narrowly necessary operational copying, while reserving general modification, sublicensing, and redistribution rights.
- Use `Copyright © 2026 Velor-dev` for public attribution without inventing a legal name or company; record separate legal-holder identification as an owner decision if needed.
- Replace contradictory current notices and README wording with consistent summaries referring to the canonical license.
- Align npm/Python metadata and propagate exact license/notice files through clean wheels, npm archives, and project-local installations.
- Add scoped third-party attribution for retained upstream materials, keeping their licenses separate and preserving downloaded toolchain notices.
- Use existing README/NOTICE and the canonical license for public authorship, consistent package author metadata, and lightweight copyright/SPDX comments in verified original source. Preserve third-party attribution, skill frontmatter, and generation boundaries; add no hidden watermarks, DRM, or provenance infrastructure.
- Replace the installation spec's blanket prohibition on licensing grants with this owner-authorized scope. Preserve `private: true`, the rejecting publication hook, and existing private-package validation.
- Keep runtime behavior, mathematical invariants, all harness integrations, customized Codex structures, and file-preservation rules unchanged.

## Capabilities

### New Capabilities

- `licensing-and-attribution`: Canonical proprietary permissions, public authorship, source attribution, third-party boundaries, and consistent public-facing notices.

### Modified Capabilities

- `cli-and-runtime`: Require explicit license metadata and exact legal-file validation in clean Python package artifacts.
- `project-installation`: Propagate approved legal materials into npm and installed projects while retaining readiness checks and publication safeguards.

## Impact

Planned changes cover root `LICENSE`, `NOTICE.txt`, `THIRD_PARTY_NOTICES.txt`, README, Python/npm metadata, original Python/Lean/JavaScript source comments, existing package build/installer paths, and package/installer tests. Maintained generation sources are used wherever generated attribution is necessary. Only planning artifacts are created by this proposal. No publication, Git operations, license-enforcement service, new runtime dependencies, public contribution policy, or expanded modification/redistribution permission is in scope.
