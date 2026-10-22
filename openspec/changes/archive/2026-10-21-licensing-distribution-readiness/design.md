# Design

## Context

See `proposal.md` for motivation. Root `NOTICE.txt` and README currently prohibit copying/modification/distribution and describe the publicly visible code as confidential and research-only. The npm package references `NOTICE.txt` as its license. `pyproject.toml` packages that notice but has no explicit license expression.

`tools/package_runtime.py` builds from isolated inputs, checks an exact archive member set, and accepts one unchanged notice in either the legacy or modern wheel license location. `tools/build_npm.py` copies the notice to package root and payload, hashes package files, and validates the actual archive. `npm/lib/install.cjs` deploys the notice at `.mathtrace/docs/NOTICE.txt`; `npm/lib/files.cjs` narrowly bounds owned destinations and provides conflict detection/recovery. These are the existing extension points; a separate legal-file framework is unnecessary.

The npm metadata, build/archive validator, and bundle loader enforce private-package status; `prepublishOnly` rejects publication. The current installation specification disallows new licensing grants, so its delta must explicitly authorize only the owner's stated permissions. This is a cross-cutting metadata/packaging change and requires a design.

## Goals / Non-Goals

**Goals:** Use a single canonical permission source, exact legal copies, and explicit metadata throughout existing build/install paths. Make operational copying unambiguous without introducing general modification or redistribution rights. Preserve owner customizations and upstream attribution, with visible attribution on verified original source.

**Non-Goals:** Enable release, add publishing automation, add license keys/click-through acceptance, hidden watermarks, DRM, a provenance registry/signing service, additional runtime dependencies, redesigned harnesses, changed mathematical gates, retroactive terms on historical artifacts, or a contribution licensing policy.

## Decisions

### 1. One custom proprietary license with a bounded operational grant

Add root `LICENSE` with the public notice `Copyright © 2026 Velor-dev`. Use a short custom license instead of MIT/Apache or an unlicensed blanket notice: permissive licenses grant broader rights, while the existing notice does not authorize intended use.

The implementation text must cover the permissions and reservations in `licensing-and-attribution`: no-charge personal/academic/commercial use, necessary local/internal operational copies and backups, and the transformations made by the intended installer. The exception covers path binding and deployment/configuration generation already performed by MathTrace, not arbitrary source or prompt edits. Preserve applicable notices. Reserve all remaining rights, including general modification, redistribution, resale, and sublicensing. Do not add unapproved patent/trademark grants or unrelated field-of-use restrictions.

Distinguish user originals/results from copied MathTrace material. Explain that public project releases must exclude installed MathTrace assets and obtain them from the official distribution instead; do not silently edit users' ignore files. Do not claim that public hosting permits absolutely no copying: acknowledge GitHub viewing/forking and service-required GitHub/npm hosting/delivery rights and mandatory legal rights without granting general off-platform redistribution.

Replace root `NOTICE.txt` with a short attribution, rights-reserved summary, and relative references to `LICENSE` and `THIRD_PARTY_NOTICES.txt`. Update current README and installation/package guidance consistently; retained historical archives remain historical. A separate legal name is not inferred from the public developer identity.

### 2. Explicit metadata, without unlocking publication

Set npm `license` to `SEE LICENSE IN LICENSE`; include all three legal files through its file list and assembly. Keep `private: true`, the rejecting publication hook, and every private-package assertion in assembly, archive validation, and bundle loading. There is no release switch or bypass in this change.

Use Python's modern `project.license = "LicenseRef-MathTrace-Proprietary"` and `project.license-files` for `LICENSE`, `NOTICE.txt`, and `THIRD_PARTY_NOTICES.txt`. Raise the setuptools build requirement from `>=68` to `>=77.0.3` to support this metadata, removing the superseded `tool.setuptools.license-files`. This only changes the isolated build dependency; runtime dependencies remain empty. A legacy free-text license field would avoid the build-floor increase but leave less precise distribution metadata.

Validate the emitted `License-Expression` and `License-File` entries against these expected values, plus exact legal-file bytes. Retain full member/RECORD/runtime/version validation and reject omitted, duplicate, altered, or unexpected legal members even if checksums are recomputed.

### 3. Reuse existing propagation and ownership checks

Copy the three maintained legal files into isolated wheel inputs, wheel license metadata storage, npm package root and payload. Include them in the existing npm hash manifest and actual tarball validation; verify nested wheel licensing through the existing wheel validator. Do not rely solely on package hashes to prove that licensing matches maintained sources.

Deploy the exact files at `.mathtrace/docs/LICENSE`, `.mathtrace/docs/NOTICE.txt`, and `.mathtrace/docs/THIRD_PARTY_NOTICES.txt` for every supported harness. These names keep relative notice links valid and avoid replacing the user's root `LICENSE`. Extend only the existing explicit owned-destination allowlist. Include all three in verification, receipts, preflight conflicts, rollback, and repeat-install/update behavior. Required legal files must remain available after checkout/cache removal.

No new skill, agent, generated prompt, routing layer, or harness structure is required. Add concise user-facing guidance in existing documentation rather than injecting licensing instructions into specialist prompts.


### 4. Scoped upstream attribution instead of blanket relicensing

Add `THIRD_PARTY_NOTICES.txt` identifying verified upstream origins and licenses. Check retained OpenSpec development skills against their actual upstream version and supply complete MIT text and verified copyright; a YAML `license: MIT` tag alone is insufficient attribution. Do not invent upstream ownership from an author tag. Record any unresolvable provenance as a release blocker rather than guessing.

Distinguish what is included in the source repository, what is bundled in the wheel/npm artifact, and what is independently installed/downloaded. OpenSpec development skills remain outside the npm runtime payload; carrying their notice in the common legal file must not imply they are bundled. Inspect harness materials for upstream copied text/code rather than treating compatibility with a harness as ownership of that harness.

Lean is downloaded by existing provisioning mechanisms and its upstream and bundled-component notices must remain intact. Python/Node/hosts/Pi extension are external prerequisites; optional Bubblewrap/libseccomp remain external. Do not add bundled copies of these dependencies or change provisioning to solve attribution. The common notice is informational for external components and does not replace their authoritative terms.

### 5. Lightweight, visible authorship without ownership overclaims

Identify `Velor-dev` as the public project author/developer in README.md and NOTICE.txt, linking to `https://github.com/Velor-dev`, with the approved copyright notice and canonical license/third-party references. Do not claim a legal name, company, sole authorship of upstream work, or proven chain of title. Align npm `author` and Python `project.authors` to Velor-dev without invented contact details; validate emitted author metadata.

Use short comments on verified original Python, Lean, and JavaScript source, including original maintained tooling/tests where appropriate:

```text
SPDX-FileCopyrightText: 2026 Velor-dev
SPDX-License-Identifier: LicenseRef-MathTrace-Proprietary
```

Wrap them in each language's comment syntax. Preserve shebang placement, encoding declarations, Python module docstrings/future imports, JavaScript strict-mode directives, and Lean import/elaboration behavior. The `LicenseRef` names the existing proposed custom license; an SPDX identifier does not add permissions or make the project open source.

Before applying headers, distinguish original maintained code from copied or mixed-origin code using existing source/provenance records, including `coding-harnesses/SOURCES.md` and `ORIGIN.json`. These records describe origins and do not themselves prove ownership. Preserve upstream notices; do not replace their SPDX identifiers with MathTrace's. Flag uncertain provenance and omit an unsupported ownership claim. No blanket repository-wide prefixing, new inventory system, or per-file ownership database is needed.

Use central authorship documents for Markdown skills, agent prompts, guides, and comment-free configuration formats rather than injecting headers into them. Keep skill YAML frontmatter and instruction bodies unchanged. If generated executable source needs attribution, update its existing maintained template/source and regenerate only its owned outputs through the existing mechanism; do not manually patch generated copies, change Codex structures, or overwrite local edits. The inspected `mathtrace.native` projection, `tools/install_native.py`, and `coding-harnesses/render.py` remain the generation authorities; this does not mandate regenerating untouched prompts.

Do not annotate historical receipts, proof/evidence archives, captured transcripts, third-party dependencies, or retained origin snapshots. Source headers can change hashes for future builds/helper compilations; use existing integrity mechanisms for the new prepared artifact and never relabel old evidence or rewrite history to match. Existing checksums validate artifact bytes, not authorship. Verify comments leave runtime semantics, generated guidance, harness discovery, and mathematical acceptance gates unchanged.

## Risks / Trade-offs

- [Public identity is not proof of legal ownership] -> Use only the authorized Velor-dev attribution. If separate legal-holder identification is needed for enforceability or release, flag it for the owner; never fabricate a name or company.
- [Accidental redistribution in public user projects] -> Explain installed software boundaries and exclusion/reinstallation in existing guidance; no new public redistribution grant.
- [Upstream provenance uncertainty] -> Verify specific retained materials and record a blocker for unsupported attribution; do not certify the whole repository from metadata alone.
- [Packaging metadata changes alter strict archive layouts] -> Update clean build staging, exact member/metadata expectations, fixture sources, and negative package tests together.
- [Legal file additions encounter local edits] -> Apply existing ownership/conflict rules, including notice updates from older installations; stop without overwriting user changes.
- [License preparation mistaken for release approval] -> Keep all safeguards and test their retention using local artifacts only.
- [Headers mistaken for provenance proof or upstream ownership] -> Restrict comments to verified original source, preserve upstream attribution, and describe public authorship accurately in README.md and NOTICE.txt.
- [Comment placement or changed source hashes disrupt operation] -> Preserve language-sensitive first lines/directives and existing generation boundaries; run regressions and fresh-build checks without rewriting historical records.

## Migration Plan

Implement the canonical documents, scoped source headers, and metadata, then extend package staging/validators and project-local propagation. Verify local wheel/tarball and independent-project installation, including repeat installs, upgrade from a prior notice-only deployment, and legal-file conflicts. Run existing regression/package/OpenSpec checks and verify skill frontmatter and generated instruction behavior are preserved. No state database or mathematical history migration is required.

Rollback a failed file deployment through existing installer journals/backups. Do not remove legal files silently or rewrite campaign/toolchain history. Previously distributed releases retain their original terms; new terms describe this prepared version. Publishing or removing safeguards requires a separate explicit release request.

## Open Questions

- Before an eventual release, does Velor-dev want or need a separate legal rights-holder identification? Public attribution and this implementation plan do not depend on inventing one. Any necessary legal-holder decision must return to the owner.
