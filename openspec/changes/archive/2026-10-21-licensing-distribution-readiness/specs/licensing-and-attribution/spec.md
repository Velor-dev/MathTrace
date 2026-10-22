# Spec Delta

## Purpose

Define MathTrace's proprietary use permissions and attribution consistently across its source distribution, packaged artifacts, and project-local installations.

## ADDED Requirements

### Requirement: Canonical proprietary license and public attribution
MathTrace SHALL provide a canonical root `LICENSE` with `Copyright © 2026 Velor-dev`. Public-facing notices SHALL describe MathTrace as proprietary and source-available, refer to this license, and remove claims of confidentiality or research-and-demonstration-only use. They SHALL NOT invent a legal name, company, or separate rights-holder identity.

#### Scenario: Reader checks the permission source
- **WHEN** a reader inspects the repository README, copyright notice, or packaged licensing summary
- **THEN** each points to the canonical license without contradictory restrictions or open-source claims
- **AND** public attribution uses Velor-dev without representing an unconfirmed legal identity

### Requirement: Free use and necessary operational copies
The license SHALL permit no-charge personal, academic, and commercial use by individuals and organizations. Permission SHALL include downloads, project-local installation, execution, updates, caches, backups, authorized internal development/CI copies, and transformations performed by the intended installer as necessary for operation, subject to retaining applicable notices.

#### Scenario: Intended project-local workflow
- **WHEN** an individual or organization uses the official installer in its project
- **THEN** necessary copying of the runtime, skills, agents, protocols, and guides and official installation transformations are permitted without a separate commercial license
- **AND** those operational permissions do not grant general source modification or redistribution rights

### Requirement: Visible authorship and source attribution
MathTrace SHALL identify Velor-dev as its public project author/developer in README.md and NOTICE.txt, with consistent package author metadata. Verified original source SHALL carry lightweight copyright/SPDX comments referencing the canonical custom license. Attribution SHALL preserve syntax, behavior, third-party notices, skill frontmatter, and historical provenance without hidden watermarks or DRM.

#### Scenario: Original source attribution
- **WHEN** maintained original Python, Lean, or JavaScript source is prepared for distribution
- **THEN** visible comments identify `2026 Velor-dev` and `SPDX-License-Identifier: LicenseRef-MathTrace-Proprietary`
- **AND** shebangs, encoding declarations, module semantics, and executable behavior remain valid

#### Scenario: Provenance boundaries
- **WHEN** third-party, mixed-origin, generated, or historical files are reviewed for attribution
- **THEN** upstream notices remain intact and uncertain ownership is flagged rather than attributed solely to Velor-dev
- **AND** generated attribution comes from maintained sources, skill frontmatter and specialist instructions remain unchanged, and historical receipts/evidence are not rewritten

#### Scenario: Attribution is descriptive
- **WHEN** a reader consults README.md, NOTICE.txt, or package author metadata
- **THEN** Velor-dev is identified as the public project author/developer without invented legal identity, exclusive ownership of upstream work, or a claim that headers alone prove provenance

### Requirement: Reserved rights and user-material boundary
The license SHALL reserve general modification, sublicensing, resale, republishing, and redistribution of MathTrace itself beyond expressly permitted operational copies, platform rights, and mandatory legal rights. Restrictions SHALL apply to MathTrace-owned material and SHALL NOT attach to users' original projects or mathematical results solely because MathTrace was used.

#### Scenario: User publishes original research
- **WHEN** a user distributes original proofs, research results, or project files created using MathTrace
- **THEN** MathTrace's license does not restrict those originals merely through tool use
- **AND** any included copies of MathTrace material remain subject to their applicable terms

#### Scenario: User distributes an installed project
- **WHEN** a user prepares a public repository or release containing installed MathTrace software assets
- **THEN** guidance identifies those assets as subject to redistribution restrictions and directs the user to exclude them and reinstall from the official distribution
- **AND** the license does not grant general public redistribution of installed skills or agents

### Requirement: Platform and third-party rights remain distinct
The license SHALL accommodate GitHub/npm service rights necessary for the intended public distribution without granting general redistribution rights. Third-party materials SHALL retain their applicable licenses and attribution, with a scoped third-party notice identifying included upstream materials separately from external prerequisites and downloaded distributions.

#### Scenario: Repository includes OpenSpec development skills
- **WHEN** MIT-licensed OpenSpec skills are retained in the public source distribution
- **THEN** their verified upstream copyright and complete MIT permission text are supplied with the distribution
- **AND** MathTrace's proprietary terms do not replace those terms or imply MathTrace ownership of those materials

#### Scenario: Installer obtains external tools
- **WHEN** the existing installer downloads the pinned official Lean archive or checks an external harness prerequisite
- **THEN** downloaded license files remain intact and external components retain their own terms
- **AND** notices distinguish these components from software bundled in the npm archive

#### Scenario: Public platform operation
- **WHEN** MathTrace is later authorized for public GitHub/npm hosting
- **THEN** the license accommodates service-required hosting, delivery, and GitHub viewing/forking rights
- **AND** these platform permissions are not represented as a general right to republish MathTrace elsewhere
