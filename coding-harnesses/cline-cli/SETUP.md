# Cline static specialist setup

Target the loader contract at source revision `e9dafbb764d0cb9acb4ef93a956ae72c350b3952`.
Check the installed CLI build before deployment: the audited loader scans `.yaml`/`.yml`,
not `.md`, despite using YAML frontmatter followed by a Markdown prompt body.
GSD's emitted `.md` files do not establish compatibility with this scanner.

Merge `.cline/agents` and `.cline/skills` into the target project root. Merge the shared
AGENTS instructions once; `.clinerules/mathtrace.md` is an additional root entry wrapper.
Preserve existing settings and external files. Restart/refresh the host and verify eleven
`math-*` definitions and eight workflows are discovered in the intended workspace.

The configured tools are named `subagent_math_referee`, `subagent_math_prover`, etc.
Call the selected tool with `prompt` containing the complete exact exported packet JSON.
The profile supplies the full role body; do not forward root history or other verdicts.
Use the actual exposed tool schema. Do not guess a generic spawn profile argument.

`tools: []` stays empty in the audited runtime filter. Worker `skills` is omitted:
declaring it, even as an empty array, adds the skills tool. `providerId` and `modelId`
are omitted; the configured tool inherits the base runtime model and thinking/effort.
No provider or effort pins are added. Confirm effective settings and tool/context scope
in the installed build before claiming qualification. Generic `spawn_agent` has broader
mode tools and is only a documented compatibility fallback, not equivalent isolation.

No host install, inference, capture backend or independent-admission qualification is
performed by rendering these files. See README.md, FALLBACK.md and shared POLICY.md.
