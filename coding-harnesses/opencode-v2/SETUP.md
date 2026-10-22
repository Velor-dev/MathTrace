# OpenCode V2 exclusive deployment

Generate this variant with `python coding-harnesses/render.py --harness opencode-v2`.
Merge only this variant's `.opencode/agents` and `.opencode/skills` into the target
project root; merge shared AGENTS instructions once. Do not deploy `opencode` at the
same time: both variants use the same discovered names and paths. Rendering is staging
only and does not switch an installed host or replace existing configuration.

V1 uses singular `permission`, with legacy `bash` and `task` action names. V2 uses
plural ordered `permissions` and `action`, `resource`, `effect`, with `shell` and
`subagent` actions. Each worker denies `*`; its Markdown filename supplies its ID.
Kilo retains its own singular permission dialect and is not an OpenCode V2 target.

Verify the installed generation and effective deny rules, model/effort and context
before dispatch. No model/effort pins or automatic routing are supplied. Eleven roles
and eight workflows are provided; native discovery is not evidence of qualified
mathematical admission. Keep shared POLICY.md and existing capture gates authoritative.
