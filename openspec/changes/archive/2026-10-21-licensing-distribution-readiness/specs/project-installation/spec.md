# Spec Delta

## MODIFIED Requirements

### Requirement: Verified readiness and distribution notices
Installation SHALL report success only after verifying payload integrity, local runtime identity, required guide paths, campaign health, pinned toolchain integrity, and selected harness prerequisites. Artifacts and installed projects SHALL retain the canonical proprietary license and required notices within owner-approved permissions. Local validation SHALL NOT depend on publication or expand those permissions.

#### Scenario: Verification failure
- **WHEN** a required check fails or cannot establish readiness
- **THEN** installation reports the failing check, recovery state, and corrective action without claiming complete success

#### Scenario: Artifact rights preservation
- **WHEN** wheel and npm artifacts are prepared for local validation
- **THEN** the canonical MathTrace license and required notices are retained without unapproved licensing terms
- **AND** private workspace data, credentials, campaign evidence, and development archives are excluded

#### Scenario: License available independently of checkout and cache
- **WHEN** any supported harness is installed and the original checkout and npm cache are unavailable
- **THEN** exact canonical license and required notice copies remain readable inside the project without network access
- **AND** the project's own root license and unrelated notices are not replaced

#### Scenario: Repeat installation and update preservation
- **WHEN** legal files are installed again or updated
- **THEN** existing ownership-aware conflict checks, recoverable deployment, and notice verification apply
- **AND** edited or unowned conflicting project files are preserved and reported

## ADDED Requirements

### Requirement: Explicit license metadata with retained publication safeguards
The npm artifact SHALL identify its included canonical custom license using file-based license metadata. Distribution-readiness changes SHALL preserve the private-package flag, rejecting publication hook, and private-package validation until release is separately authorized. Installation tests SHALL use local artifacts without publishing or adding a release bypass.

#### Scenario: Local package remains usable and unpublished
- **WHEN** the package is assembled, packed, validated, and executed in an independent project
- **THEN** the canonical license reference resolves inside the archive and installation completes under existing prerequisites
- **AND** the package remains private with its rejecting publication hook and private-package validation intact

#### Scenario: Licensing preparation does not authorize release
- **WHEN** license metadata, documentation, or legal-file propagation is updated
- **THEN** no publication safeguard is removed, bypassed, or automatically enabled for release
- **AND** documentation distinguishes local readiness validation from separately authorized GitHub/npm publication
