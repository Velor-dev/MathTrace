# Spec Delta

## MODIFIED Requirements

### Requirement: Self-contained installation payload

The installer SHALL bundle a version-matched verified Python wheel and the selected harness's complete required asset closure. Installed runtime invocation, skills, agents, guides, and references SHALL resolve independently of the MathTrace source checkout and npm cache. The installer SHALL NOT create `coding-harnesses/` in the target project root, SHALL locate shared references under `.mathtrace/`, and SHALL provide visible progress during provisioning without production npm dependencies.

#### Scenario: Source checkout and npm cache are unavailable
- **WHEN** installation completes and the source checkout and original npm package directory are unavailable
- **THEN** the installed launcher runs the expected local MathTrace runtime and all required harness references resolve within the installed project
- **AND** runtime execution requires no environment activation or global PATH modification

#### Scenario: Complete harness inventory
- **WHEN** each supported harness payload is installed in its documented supported environment
- **THEN** its existing eight skills and applicable specialist bindings are available with their required shared assets
- **AND** mutually exclusive OpenCode versions are not activated together

#### Scenario: Uncluttered project root
- **WHEN** any supported harness (such as Antigravity, Claude Code, Cursor, or Devin) is installed into a target project
- **THEN** no `coding-harnesses/` directory is created in the target project root
- **AND** any required shared guides, policies, or protocol references are deployed under `.mathtrace/` rather than the project root

#### Scenario: Visible provisioning progress
- **WHEN** installation initiates Python runtime environment creation, wheel installation, or Lean 4 toolchain downloading and extraction
- **THEN** user-visible status progress messages are emitted to stdout before and during each operation
- **AND** the terminal does not remain silently stalled during network downloads or archive extraction
