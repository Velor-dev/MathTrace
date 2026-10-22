# Command Code setup and binding

Researched **2026-10-15**. This targets [Command Code](https://github.com/CommandCodeAI/command-code), a separate product. Its public repository's README links to the vendor documentation; the inspected root contains documentation/mods rather than the agent-loader implementation. Schema/default findings below are documented behavior, not a source-code or live-runtime verification claim. This adapter uses neither Claude files nor Pi's extension/provider.

## Install and place files

Follow the official [quickstart](https://commandcode.ai/docs/quickstart): Node.js 22+, the `command-code` package and authentication are prerequisites. The full launcher name is `command-code`; its short alias is `cmd` on macOS/Linux/WSL and `cmdc` on native Windows. No installer, login or host command is executed by this packaging task.

Merge this adapter's `.commandcode/agents/` and `.commandcode/skills/` into the **target project root**, preserving existing files. Keep `coding-harnesses/shared/` in that project. Merge the shared [project instruction section](../shared/project-instructions.md) into the existing root `AGENTS.md` once. Command Code's [memory documentation](https://commandcode.ai/docs/memory) selects root `AGENTS.md` first, then `.commandcode/AGENTS.md` if the root file is absent. It does not read `CLAUDE.md` for this purpose. No duplicate memory file is supplied. Launch from the target project root, not this nested staging directory, and handle project trust through the normal host prompt.

## Agents

The eleven project definitions use `.commandcode/agents/math-*.md`. They follow Command Code's [custom-agent schema](https://commandcode.ai/docs/agents): YAML frontmatter followed by the system-prompt body. Every definition supplies the existing role's `name` and `description`, followed by the complete unchanged shared role body. No Claude-only, Pi-only, model-routing or invented inheritance keys are added.

The documented fields also include `tools`, `disallowedTools`, `model`, `reasoningEffort`, `maxTurns`, `permissionMode`, `background` and `showOutput`. This payload omits them. In particular, **omitted `tools` means no tools** in Command Code; the role's tool-free policy remains unchanged. This differs from Pi's extension and must not be translated between products. Effective enforcement/context has not been observed here.

Definitions are re-scanned each turn. Bundled definitions load before personal `~/.commandcode/agents/`, then project `.commandcode/agents/`; the first matching name wins. Check the effective `math-*` definitions in `/agents` after deployment: a personal definition can shadow a project role. Do not silently use a replacement or a built-in General/Explore/Plan worker when the intended role is absent or shadowed.

## Skills

Each of the eight wrappers is `.commandcode/skills/<name>/SKILL.md`, with YAML `name` and `description`, and a Markdown body referencing the shared instruction. Names match their directories. The [skill documentation](https://commandcode.ai/docs/skills) also confirms `.agents/skills/` discovery. This package uses the native directory only, keeping one obvious Command Code wrapper per skill and leaving the root managed `.agents/` untouched.

Discovery precedence is project `.commandcode/skills`, project `.agents/skills`, user `~/.commandcode/skills`, then user `~/.agents/skills` before extra/bundled locations. Existing compatible skills may therefore be discovered too; resolve duplicate-name warnings deliberately. Invoke an existing skill by `/<name>`; if a built-in/custom command owns that name, use `/skill:<name>`. This is host invocation syntax for the existing eight skills, not a new command set. No skill model/effort pins are supplied. Help still only displays the existing reference and starts no work.

## Delegation and protocol

Root follows the shared skill and [protocol](../shared/PROTOCOL.md), subject to [POLICY](../shared/POLICY.md)'s transport boundary. The [native tool reference](https://commandcode.ai/docs/reference/tools) defines the `agent` call with required `description` and `prompt`, optional `subagent_type`, optional model override and optional background flag. Select the exact registered `math-*` role; its `prompt` receives the **complete exported task packet unchanged**. For example, after choosing a task that actually calls for a referee:

```json
{
  "description": "Assess exact frozen argument",
  "subagent_type": "math-referee",
  "prompt": "<complete exported task packet JSON>"
}
```

Replace the placeholder with the actual packet, including exact task identity/hash, without root conversation, other verdicts, favored-route narrative or build history. The system-prompt body already contains the existing JSON result contract; workers need not read shared files. Never substitute Antigravity reserve/capture calls for this native tool.

Independent tasks may use multiple `agent` calls in one turn; this does not require every role or introduce a fixed research sequence. Background calls return an `agent_id`; root retains it and collects actual terminal output via `agent_output` (`wait`/`status`). A timeout is not completion or permission to redispatch. Root still assesses output, mediates checking/execution and owns canonical commits. Children cannot use `agent` or `agent_output`; documentation describes one-level delegation. Separate context windows do not by themselves prove complete input isolation.

## Model and effort limitation

Omitting `model` inherits the active conversation model, which may be the host's planning/implementation selection. MathTrace does not select or alter those settings. **The documented omitted `reasoningEffort` default is the model's default effort, not the session's selected `/effort`.** No parent-effort inheritance flag is documented in the agent schema. This is a concrete Command Code capability limit, not a reopening of the resolved Antigravity or Pi observations.

Keep model/effort overrides absent. Disclose this mismatch before using the adapter for delegated work. If exact parent-effort preservation is required, keep delegation blocked until the user selects a compatible host configuration or manually changes their agent configuration. Do not claim that omission preserves both settings, silently compensate with a pinned effort, invent `reasoningEffort: inherit`, or replace required independent workers with root self-review.

No producer-bound Command Code capture/admission backend is added. Returned output retains honest exploratory/operator provenance and cannot qualify independent reviews or bypass audit/release/fulfillment gates. Learned taste/memory remains host advice, never canonical mathematical evidence; effective worker input exposure is unverified. No host run, special tests, package build or main-runtime change accompanies this adapter.
