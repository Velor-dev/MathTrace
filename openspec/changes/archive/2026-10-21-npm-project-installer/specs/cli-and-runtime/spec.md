# Spec Delta

## MODIFIED Requirements

### Requirement: Isolated Package Build and Distribution
The system SHALL support building and installing the `mathtrace` Python package as a self-contained distribution wheel with verified file checksums. Package validation SHALL verify the complete archive against the intended runtime, required notices, and valid distribution metadata, rejecting unexpected packages, duplicate or unsafe paths, and stale build content.

#### Scenario: Package wheel generation
- **WHEN** package validation or build tools run
- **THEN** standard wheel artifacts are created under `dist/` or transient build roots without polluting source directories
- **AND** release wheels are built from clean isolated inputs rather than reusing stale build output

#### Scenario: Bytecode and asset fidelity verification
- **WHEN** an installed package wheel is validated
- **THEN** package tools verify that installed modules, assets, and entry points exactly match source definitions
- **AND** validation checks the entire archive member set, required notices, metadata, and recorded checksums rather than only the `mathtrace/` subtree

#### Scenario: Legacy package contamination is rejected
- **WHEN** stale build output contains a legacy `gsd_math` tree or another unapproved package
- **THEN** the clean release build excludes that content
- **AND** validation rejects any wheel into which it is injected even when the current `mathtrace/` files match source

#### Scenario: Unexpected or unsafe archive members
- **WHEN** an archive contains duplicate members, redirected or escaping paths, unapproved files, or mismatched entry points or version metadata
- **THEN** validation fails before that artifact is accepted for installer bundling
