# Current Kimi Code setup and legacy staging migration

This payload targets Node Kimi Code (`MoonshotAI/kimi-code`), not the archived Python
`kimi-cli`. Merge `.kimi-code/agents` and `.kimi-code/skills` into the target project.
Eleven Markdown profiles and eight workflows are supplied. Keep the shared role/skill
library in `coding-harnesses/shared` and merge AGENTS instructions once.

Start a fresh host session from the target project and verify discovery. Project roots
follow the installed version's repository-root rules; do not assume a checkout without
`.git` has identical discovery. User roots are `$KIMI_CODE_HOME/agents` and `/skills`
(default `~/.kimi-code`); generic `.agents` roots can cause name collisions. Additional
agent directories use `extra_agent_dirs` in config.toml, not an assumed `--agents-dir`.
No legacy `.kimi/mathtrace.yaml` launch is used. Select a discovered `math-*` profile
through the native Agent tool with the exact task packet in its prompt.

`tools: []` denies tools and `subagents: []` denies nested delegation. Model/provider/
effort fields are omitted; without a secondary-model pool/force override, model and
thinking inherit. A configured secondary pool changes omission semantics. Verify those
settings rather than enabling a router or pinning a provider model. Do not interpolate
`${base_prompt}` into self-contained worker bodies or add foreign model/mode fields.

The renderer's optional staging-only migration is:

```text
python coding-harnesses/render.py --harness kimi-code --migrate-kimi-legacy
```

It checks every known old generated path against `legacy-kimi-files.json` before
removing any matching files. Modified/redirected candidates abort cleanup; unknown
files and directories remain. Default rendering never deletes. This command does not
migrate an installed project's `.kimi`, home settings or credentials. Preserve and
reconcile any installed legacy customizations manually before switching products.

These payloads do not establish live host qualification or producer-bound admission.
