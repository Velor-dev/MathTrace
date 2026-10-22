# Hermes project-local installation prerequisite

Before running the MathTrace installer, add the planned project's absolute
`coding-harnesses/hermes-agent/skills` path to `skills.external_dirs` in the chosen
Hermes profile's config.yaml. Use the existing config.example.yaml binding with
MATHTRACE_WORKSPACE set, or an absolute path. The destination can be configured
before the project files exist. Launch Hermes from that project.

The installer reads the selected HERMES_HOME/config.yaml or default profile without
printing credentials. It accepts the documented simple YAML list or JSON-compatible
YAML; unrecognized complex syntax stops with instructions. It never edits the
profile, home directory or credentials. Prepare the binding externally and rerun.
Installation checks do not establish independent-review capture or tool isolation.
