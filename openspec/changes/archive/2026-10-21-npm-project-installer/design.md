# Design

## Context

See `proposal.md` for motivation and the two delta specs for acceptance behavior. There is no npm package today. `pyproject.toml` defines a pure Python 3.11+ runtime with no third-party runtime dependencies; the wheel carries Python modules and `lean_inspector.lean`, not deployment assets. A retained wheel contains stale `gsd_math/` alongside `mathtrace/`; `build/lib` contains both, and `tools/validate_package.py` only compares the latter subtree.

`coding-harnesses/research.json` describes 18 payloads for 17 products. Shared wrappers reference project-root `coding-harnesses/shared/` and the selected harness README. `render.py` generates staging assets, preserves Codex conflicts, and excludes the frozen Antigravity projection. Native capture compares installed role bytes with `mathtrace.native.runtime_files()`. `tools/install_native.py` replaces its owned `.agents` tree and cannot safely deploy to arbitrary mixed user directories unchanged.

Existing `init` refuses an existing store. `install_lean` requires a store, downloads the official exact-release target ZIP with its publisher digest, publishes a fresh distribution tree, and appends a toolchain record. The supported checking profile pins Lean `v4.30.0`. Thus toolchain provisioning is a durable campaign operation, not a filesystem-only installer step.

The user resolved the external-write boundary: check existing host setup, stop with precise instructions when missing, and keep all installer-controlled writes in the project. Package-manager caches used by npx itself are outside this deployment ownership boundary.

## Goals / Non-Goals

**Goals:** Keep the npm interface small, bundle coherent release inputs, install one selected integration, use existing Python/runtime semantics, and make file ownership and recovery explicit. Verify installation without source-checkout or npm-cache access.

**Non-Goals:** Automatic Python, host application, credential, plugin, or extension installation; home/profile writes; global MathTrace setup; new mathematical workflows, capture backends, model routing, or verification guarantees; registry publishing or licensing decisions. No uninstaller, update daemon, telemetry, plugin registry, or multi-harness migration framework is needed.

## Decisions

### 1. Thin Node entry point and a bundled release

Add an isolated npm package directory, proposed as `npm/`, with `bin/install.cjs` as the single `mathtrace` executable, using Node built-ins and no production npm dependencies. Use Node 22+ as the installer baseline and Python 3.11+ as the runtime baseline; individual hosts can require newer versions. Invocation targets the real current directory, not an inferred ancestor or package-cache directory. The normal command presents a numbered menu derived from the bundled inventory. Provide `--harness <id>` for deterministic automation and tests; EOF/cancellation performs no active deployment, and invalid input never silently selects a default. Non-interactive invocation requires that flag.

The release builder bundles exactly one wheel and pre-generated maintained payloads, shared assets, the selected documentation closure, and notices for all selectable harnesses. The installed project receives only the chosen active payload plus its dependencies. A bundled manifest pins npm/Python versions, Lean release, harness inventory, file destinations and hashes. Fail on version disagreement. Do not install from PyPI, fetch a source branch, build a wheel on the user's machine, or run rendering there. Use subprocess argument arrays, not shell-composed commands. No install/postinstall hook is required; the explicit binary performs installation.

Alternative: downloading wheel and assets independently is smaller on npm but adds endpoints, authorization, and version skew. The existing assets are small enough to bundle. Avoid copying GSD's broad installer architecture.

### 2. Private environment and durable launcher

Use `.mathtrace/` as a reserved installer-owned project directory, separate from `.math/` campaign data and the user's `.venv`. Proposed contents are `install.json`, a deployment journal/backups, `runtime/<release-and-wheel-digest>/` environments, and `run.cjs`. A versioned environment is created at its final location and never moved. Discover and probe actual Python executables (`py -3`, `python3`, `python` as applicable), verify version and `venv`/pip support, then install the bundled wheel with isolated pip configuration, `--no-index`, and no dependency resolution. Keep temporary files/caches inside the project. Missing prerequisites produce OS-appropriate instructions; do not bootstrap Python or download arbitrary pip scripts.

`node .mathtrace/run.cjs <existing-operation> ...` resolves its own project-local manifest, executes the owned interpreter with `-I -m mathtrace`, forwards arguments/exit status, and uses the project root as working directory. It does not implement new mathematical commands. Installation verifies the exact module location and version, not merely a successful import from the developer environment. Store the original interpreter identity and report a moved-project or missing-interpreter environment as requiring recreation through reinstall. No activation or global PATH edits are needed.

Installed root instructions must use the launcher. Apply a bounded, maintained deployment substitution for literal `python -m mathtrace` commands in root-facing protocol/help/docs and project instructions; the source-checkout documentation retains its existing command. Record transformed content hashes. Do not transform specialist role bodies, exact task packets, evidence, or existing campaign files. This ensures Antigravity's role-byte checks remain valid. Installed instructions clearly identify this command binding and preserve all mathematical mandates. Test that no operational instruction requires ambient Python or a source-only utility.

### 3. Bootstrap through existing state and toolchain APIs

After read-only preflight, use the new owned interpreter to initialize `.math/state.sqlite` only if absent. If present, validate health/schema and fail without replacing an invalid or incompatible store. Inspect toolchain records for the exact pinned release and execution target; verify full manifests and reuse a valid installed record. An installer receipt's identifier is a hint, not an alternative trust root. If no matching toolchain exists, invoke existing `install_lean`; preserve all old records and trees. Record the resulting identifier and backend in the installation receipt.

Default provisioning explicitly targets `direct`, without probing optional sandbox services. Expose the existing optional mode through `--execution-mode bubblewrap`; check its supported Linux/WSL prerequisites and report missing setup without installing host dependencies. Keep default runtime mode unchanged: campaign operation JSON continues to select Bubblewrap explicitly. Native and sandbox toolchains can coexist; do not repurpose an old record or reinterpret historical attempts.

Initialization and provisioning are append-only side effects. Never restore a database snapshot as file-deployment rollback. On provisioning failure retain any valid initialized store, verified toolchains, and provenance, report their state, and let retry inspect/reuse them. Do not create claims/contracts or qualify mathematical evidence during setup.

### 4. Deploy existing harness layouts and the full dependency closure

Use the inventory and generated assets as inputs to a small explicit destination mapping, not a new adapter framework. Preserve `coding-harnesses/shared/` and selected harness documentation at their established paths. Include required catalog/policy/guide references and operational docs. Relocate packaged docs under an installer-owned documentation location and rebase installed links if the target already owns `docs/`; never commandeer the target's documentation tree. Install only the selected native discovery directories. For dynamic-only adapters, install the shared role library and existing binding guidance instead of inventing static agents.

For Codex retain `.codex/agents/*.{toml,md}` and the owner's existing skill location. Fresh deployments use `.codex/skills`, with `.agents/skills` compatibility selected only explicitly or from an unambiguous existing layout. Never overwrite a managed Antigravity tree or auto-enable duplicate same-name wrappers. Modified role/skill collisions stop preflight and remain intact; preservation does not imply that altered role bytes satisfy runtime qualification. For Antigravity use authoritative wheel-native generation for release assets and exact role bodies; do not ship a stale ownership manifest or historical snapshot receipt as a fresh installation attestation. The frozen source snapshot and ORIGIN records remain untouched.

Merge a clearly delimited MathTrace section once into supported root project instructions, preserving all bytes outside it. Honor existing host loading rules; do not create a substitute `CLAUDE.md` or overwrite settings. OpenCode V1/V2 share discovery destinations and must be selected exclusively; an incompatible existing deployment blocks installation. Re-running a different harness selection is not automatic migration: stop with guidance if the previous recorded harness differs.

### 5. Preflight external requirements without external writes

Before creating active project files or provisioning state, check the selected installed host version and documented loading prerequisites where applicable. Add only minimal declarative prerequisite data beside the existing inventory; no live network product research or generic plugin manager belongs in installation. Read configuration without logging secrets. Distinguish missing/unverifiable configuration from a qualified native run.

Pi must already have its compatible upstream `index.ts` and `agents.ts` extension and project-agent loading available. Hermes must already resolve its external skill source to the planned project path with the correct workspace binding; the user can configure that path before it exists and rerun. Claude must meet the documented instruction-loading mode; other hosts retain their existing setup/limitation checks. When no safe deterministic verification is available, stop and identify the exact required check rather than treat a user assertion as proof. Tests supply representative host/config fixtures; no credentials or model session is required for installer validation.

The installer does not promise that every host/version is qualified for independent mathematical evidence. Existing inherited-model, tool/context isolation, and capture limits remain explicit after successful deployment. Host authentication and usage still belong to the user.

### 6. File ownership, conflict detection, and recovery

Acquire a project installation lock, canonicalize the target, reject symlink/junction/redirection components at all planned destinations, and compare a complete file plan before mutation. Stop on unowned differing files or modified previously owned files; identical unowned payload files can be left in place without claiming ownership. Do not trust an existing manifest alone to authorize deletion outside the known payload destinations. A malformed installation receipt blocks updates.

Stage payload bytes and verify hashes. Create versioned runtime environments at their final project-local paths while leaving the prior active runtime intact. Keep a small durable journal and backups for files actually changed, including the managed instruction section. Recheck destination hashes immediately before replacement. Publish the active receipt last. Roll back touched deployment files on ordinary failure and detect an incomplete journal on rerun; restore only when the current bytes match the interrupted install's recorded writes, otherwise stop with precise recovery guidance. Fail concurrent installation rather than guessing stale-lock ownership.

Unchanged reinstall verifies/reuses owned files, the private runtime, instructions, and toolchain, with no duplicated sections or toolchain events. Update removes only obsolete unchanged owned payload files, never foreign directory trees. Retain old runtime environments and toolchain trees for historical execution recovery; no automatic garbage collector is added. A move or changed base interpreter requires recreating an environment, not relocating it. Campaign DB changes are reconciled through existing append-only semantics, independently of file rollback.

### 7. Clean packaging and rights preservation

Build wheels from a fresh allowlisted source staging tree using the existing build backend; never delete retained historical archives to clean the workspace. Strengthen `tools/validate_package.py` to verify every archive member, reject duplicate/escaping/symlink entries and unapproved top-level packages such as `gsd_math`, check valid distribution metadata/entry points/RECORD hashes, and compare exact current modules plus Lean helper and notices. Test both a dirty source build tree and an injected contaminated wheel. Validate installed identity outside the checkout.

The npm pack allowlist includes hidden harness assets deliberately and excludes build leftovers, `.math`, `.venv`, work archives, credentials, OpenSpec development skills, and source-only governance. Inspect the actual tarball, not only the file list configuration. Keep existing MathTrace rights-reserved notice text verbatim in both artifacts and use truthful non-open-source metadata; no generated license grants or reused GSD license. Bundled third-party notices, if any, are retained separately. Publication is disabled during development/local validation and is not an implementation task; registry naming and distribution permission remain the owner's later release decision. Local `npm pack` and packed-artifact execution provide acceptance without publishing.

## Risks / Trade-offs

- External prerequisites can prevent a one-command finish on an unprepared host → fail during read-only preflight with exact setup instructions; all installer writes stay project-local as explicitly chosen.
- Lean downloads are large and network/publisher failures are possible → use existing digests, target checks and retained provisioning state; do not weaken verification to finish setup.
- Runtime updates affect historical recorder identities → retain prior environments and receipt identities; do not rewrite old evidence or guarantee currentness across versions.
- Cross-file deployment is not one atomic filesystem operation → lock, journal, backup, receipt-last activation, and tested interruption recovery make the state explicit.
- Config/host contracts vary and can change → pin the release's supported contracts, fail unknown versions or unverifiable requirements honestly, and keep checks small and harness-specific.
- Rights-reserved visibility does not grant distribution rights → preserve existing text, exclude publication, and leave permission decisions to the owner.

## Migration Plan

First fix and test wheel assembly/validation. Add npm payload assembly and the minimal local installer, then integrate runtime provisioning, all harness mappings, and preservation/recovery checks. Update maintained deployment guidance and installed command bindings without changing specialist bodies. Validate the packed artifact in unrelated temporary projects with the source checkout and npm package directory unavailable after install.

Existing source-checkout installations continue using their current commands and managed native installer. The new installer does not adopt or replace their ownership receipt automatically; matching unowned files remain unowned, and conflicting customized layouts stop safely. Update rollback restores the last verified file deployment and active runtime selection; valid campaign/toolchain events remain retained. No commit, registry publication, or deployment to the owner's working project is required for acceptance.
