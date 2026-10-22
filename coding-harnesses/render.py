"""Render only this directory's documentation/configuration payloads.

No host execution, runtime import, installation or tests. Shared role/skill
snapshots and research.json are inputs. The Antigravity copy is never rewritten.
Deletion is limited to opt-in, hash-verified legacy Kimi staging migration.
"""
from pathlib import Path
import argparse
import hashlib
import json

BASE = Path(__file__).resolve().parent
CATALOG = json.loads((BASE / "catalog.json").read_text(encoding="utf-8"))
RESEARCH = json.loads((BASE / "research.json").read_text(encoding="utf-8"))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--harness", choices=[h["id"] for h in RESEARCH["harnesses"]])
parser.add_argument("--migrate-kimi-legacy", action="store_true",
                    help="Retire only exact known generated legacy .kimi staging files; preserve conflicts")
ARGS = parser.parse_args()
SELECTED = ARGS.harness


def migrate_kimi_legacy():
    if SELECTED not in (None, "kimi-code"):
        parser.error("--migrate-kimi-legacy requires --harness kimi-code or all harnesses")
    manifest = json.loads((BASE / "legacy-kimi-files.json").read_text(encoding="utf-8"))
    pending = []
    conflicts = []
    root = BASE.resolve()
    for relative, digest in manifest["files"].items():
        path = Path(relative)
        if path.is_absolute() or path.parts[:2] != ("kimi-code", ".kimi") or ".." in path.parts:
            conflicts.append(relative)
            continue
        target = BASE / path
        # Reject any redirected component, including dangling links and Windows junctions.
        components = [BASE.joinpath(*path.parts[:i]) for i in range(1, len(path.parts) + 1)]
        if (any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()) for p in components)
                or target.resolve() != root / path):
            conflicts.append(relative)
        elif target.exists():
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                conflicts.append(relative)
            else:
                pending.append(target)
    if conflicts:
        parser.error("Legacy migration preserved all files; conflicting/redirected paths: " + ", ".join(conflicts))
    # All candidates are checked before unlinking; no directory or unknown file is removed.
    for target in pending:
        target.unlink()


if ARGS.migrate_kimi_legacy:
    migrate_kimi_legacy()


def write(relative, content):
    if SELECTED and Path(relative).parts[0] not in (SELECTED, "SOURCES.md"):
        return
    target = BASE / relative
    normalized = content.rstrip() + "\n"
    if Path(relative).parts[0] == 'codex' and target.is_file():
        previous = target.read_text(encoding='utf-8')
        codex = next(h for h in RESEARCH['harnesses'] if h['id'] == 'codex')
        key = Path(*Path(relative).parts[1:]).as_posix()
        if (key.startswith(('.codex/', '.agents/')) and previous != normalized
                and hashlib.sha256(previous.encode()).hexdigest()
                    != codex.get('preserved_generated_hashes', {}).get(key)):
            raise ValueError('Preserved conflicting owner Codex payload: ' + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(normalized, encoding="utf-8", newline="\n")


def scalar(value):
    # JSON strings are also valid YAML scalars and TOML basic strings.
    return json.dumps(value, ensure_ascii=False)


def frontmatter(fields, body):
    return "---\n" + "\n".join(fields) + "\n---\n\n" + body


def skills(harness):
    slug = harness["id"]
    for name, description in CATALOG["skills"].items():
        if name == "mathtrace-help":
            body = (
                "Read `coding-harnesses/shared/help.md` from the project root and display "
                "only its `<reference>` content, as required by "
                "`coding-harnesses/shared/skills/mathtrace-help/SKILL.md`. "
                "Do not inspect or initialize a campaign, delegate, run checking, or suggest next steps. "
                "The guide uses the existing skill names; invocation syntax depends on the host.\n"
            )
        else:
            body = (
                f"Read `coding-harnesses/shared/POLICY.md` and `coding-harnesses/{slug}/README.md` "
                f"from the project root, then follow `coding-harnesses/shared/skills/{name}/SKILL.md` "
                "for this request. Preserve the existing workflow and exact user arguments. "
                "Use only the documented host binding; Antigravity reservation/capture is not portable. "
                "Unavailable independent evidence remains a gate limitation.\n"
            )
        write(Path(slug) / harness["skill_dir"] / name / "SKILL.md", frontmatter(
            [f"name: {name}", f"description: {scalar(description)}"], body))
        if slug == 'codex':
            write(Path(slug) / '.codex/skills' / name / 'SKILL.md', frontmatter(
                [f"name: {name}", f"description: {scalar(description)}"], body))


def agents(slug):
    for name, description in CATALOG["roles"].items():
        body = (BASE / "shared/roles" / f"{name}.md").read_text(encoding="utf-8")
        common = [f"name: {name}", f"description: {scalar(description)}"]
        if slug == "codex":
            write(Path(slug) / ".codex/agents" / f"{name}.toml",
                  f"name = {scalar(name)}\ndescription = {scalar(description)}\n"
                  f"developer_instructions = {scalar(body)}\n")
            role_header = (
                f"<codex_agent_role>\n"
                f"role: {name}\n"
                f"tools: none\n"
                f"purpose: {description}\n"
                f"</codex_agent_role>\n\n"
            )
            write(Path(slug) / ".codex/agents" / f"{name}.md",
                  frontmatter([f'name: "{name}"', f'description: {scalar(description)}'],
                              role_header + body))
        elif slug == "command-code":
            # Command Code documents omitted tools as none, omitted model as
            # inherit, and omitted reasoningEffort as model default (see SETUP).
            write(Path(slug) / ".commandcode/agents" / f"{name}.md", frontmatter(common, body))
        elif slug == "devin":
            # Host compatibility is a root-facing dispatch prerequisite, not a body rewrite.
            write(Path(slug) / ".devin/agents" / f"{name}.md", frontmatter(
                common + ["allowed-tools: []"], body))
        elif slug == "claude-code":
            write(Path(slug) / ".claude/agents" / f"{name}.md", frontmatter(
                common + ["tools: []", "model: inherit", "omitClaudeMd: true"], body))
        elif slug == "grok-build":
            write(Path(slug) / ".grok/agents" / f"{name}.md", frontmatter(
                common + ["tools: []", "promptMode: full", "agentsMd: false"], body))
        elif slug == "cursor":
            write(Path(slug) / ".cursor/agents" / f"{name}.md", frontmatter(
                common + ["model: inherit", "readonly: true"], body))
        elif slug in ("opencode", "kilo"):
            native = ".opencode" if slug == "opencode" else ".kilo"
            write(Path(slug) / native / "agents" / f"{name}.md", frontmatter(
                [f"description: {scalar(description)}", "mode: subagent", "permission:", '  "*": deny'], body))
        elif slug == "opencode-v2":
            write(Path(slug) / ".opencode/agents" / f"{name}.md", frontmatter(
                [f"description: {scalar(description)}", "mode: subagent", "permissions:",
                 '  - action: "*"', '    resource: "*"', "    effect: deny"], body))
        elif slug == "omp":
            write(Path(slug) / ".omp/agents" / f"{name}.md", frontmatter(
                common + ["tools: []", "spawns: []"], body))
        elif slug == "pi":
            # Official example parses an empty tools list as undefined/defaults.
            # Preserve the role's assigned policy without inventing a deny field.
            write(Path(slug) / ".pi/agents" / f"{name}.md", frontmatter(common, body))
        elif slug == "kimi-code":
            write(Path(slug) / ".kimi-code/agents" / f"{name}.md", frontmatter(
                common + ["tools: []", "subagents: []"], body))
        elif slug == "cline-cli":
            # Audited Cline loader scans .yaml/.yml with frontmatter plus prompt body.
            # Declaring skills (even []) adds a skills tool, so omit it entirely.
            write(Path(slug) / ".cline/agents" / f"{name}.yaml", frontmatter(
                common + ["tools: []"], body))


def readme(harness):
    slug = harness["id"]
    def cell(value):
        return value.replace("<", "&lt;").replace(">", "&gt;").replace("|", "\\|")
    sources = "\n".join(f"- [Official source {i}]({url})" for i, url in enumerate(harness["sources"], 1))
    revision = f"\nSource revision observed: `{harness['revision']}`.\n" if "revision" in harness else ""
    setup = "\nPi-specific installation, scope and exact tool binding: [SETUP.md](SETUP.md).\n" if slug == "pi" else ""
    if slug == "command-code":
        setup = "\nCommand Code installation, schemas, discovery and model/effort limits: [SETUP.md](SETUP.md).\n"
    if slug in ("devin", "muse-code", "cline-cli", "kimi-code", "opencode", "opencode-v2"):
        setup = "\nNative setup, role binding and unsupported features: [SETUP.md](SETUP.md).\n"
    return f"""# {harness['name']} adapter

Research date: {harness.get('research_date', RESEARCH['date'])}. Target: {harness['identity']}.
{revision}
| Feature | Confirmed binding / scope |
|---|---|
| Project instructions | {cell(harness['instructions'])} |
| Skills / commands | {cell(harness['skills'])} |
| Custom agents | {cell(harness['agents'])} |
| Delegation | {cell(harness['delegation'])} |

{harness['install']}
{setup}

For shared project instructions, merge [project-instructions.md](../shared/project-instructions.md) into the target project's `AGENTS.md` where the host supports it. Cline also supplies a native rule wrapper; merge the instructions once. Keep `coding-harnesses/shared/` at the same project-relative path. See [deployment instructions](../README.md) before copying anything.

Use only the existing [eight skills](../shared/help.md) and [eleven role prompts](../shared/roles/). Read [POLICY](../shared/POLICY.md) before mathematical operation. Root intake/clarification, state inspection, canonical commits and execution mediation stay inline as already specified; delegate only work the existing skills/protocol actually require. No new phases or automatic full-roster dispatch are introduced.

Limitations: {harness['limits']}

These are documentation/configuration payloads, not evidence of a live host run or mathematical qualification. Except for the preserved original Antigravity build's already recorded scope, no adapter supplies producer-bound capture/admission support. Do not replace missing independent evidence with root self-review or manual receipt fabrication.

Official sources consulted:

{sources}
"""


def fallback(harness):
    binding = ("The audited static binding is supplied; use [SETUP.md](SETUP.md) for version checks and named tools. "
               "Only if that binding is unavailable on the installed surface, use its documented fresh dynamic spawn with the full role text."
               if harness["id"] == "cline-cli" else "No unconfirmed static custom-agent file schema is shipped.")
    return f"""# {harness['name']} role binding and inline fallback

Native delegation: {harness['delegation']}

{binding} The complete existing role definitions are in `coding-harnesses/shared/roles/`; [catalog.json](../catalog.json) lists their names and purposes.

For a supported dynamic delegate, root reads exactly the selected role body and places its full text in the child instruction/prompt input exposed by the host. Append the **complete exported task packet unchanged**, not a summary or selected fields. Keep task_id and packet_hash intact. Use a new context, not a history-inheriting fork. Do not forward the root conversation, other verdicts, campaign/build archives or all skills. Omit model/effort overrides. Request the role's existing single-JSON-object response. Root retains actual returned handles and outputs with honest provenance; this is not a qualified Antigravity capture.

Use only the actual tool schema available in the installed version/profile; this guide does not invent dynamic spawn parameters. If fresh delegation is absent or exposes incompatible context/settings, report that limitation and keep the relevant independent-review gate blocked. For Pi core, delegation is absent by design; an extension would be separately chosen work.

Inline fallback: root may read the selected role prompt and perform explicitly labeled exploration or critique in the current context. Explain that this is root work. Do not label it an independent referee, reproducer, fidelity assessment or adjudication, and do not use it to satisfy independent audit/release/completion requirements. Preserve the original skills' behavior and stopping conditions; do not silently flatten required independent work.

Read [POLICY](../shared/POLICY.md) for the unchanged mathematical and capture limits. {harness['limits']}
"""


for harness in RESEARCH["harnesses"]:
    slug = harness["id"]
    if slug != "antigravity":
        skills(harness)
        agents(slug)
    if slug in ("primeagent", "cline-cli", "dsh", "hermes-agent"):
        write(Path(slug) / "FALLBACK.md", fallback(harness))
    write(Path(slug) / "README.md", readme(harness))

write("claude-code/launch-settings.json", json.dumps({
    "pluginConfigs": {"cc-plugin-agents-md@builtin": {
        "options": {"instructionFiles": "claude-md-and-agents-md"}}}}, indent=2))

write("cline-cli/.clinerules/mathtrace.md", """# MathTrace

For a MathTrace request, read `coding-harnesses/shared/project-instructions.md`,
`coding-harnesses/shared/POLICY.md` and `coding-harnesses/cline-cli/README.md`
from the project root. Follow only the relevant existing shared skill.
This is a root rule; do not include it in blind worker prompts.
""")

write("cline-cli/SETUP.md", """# Cline static specialist setup

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
""")

write("kimi-code/SETUP.md", """# Current Kimi Code setup and legacy staging migration

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
""")

for slug, version, other in (("opencode", "V1", "opencode-v2"),
                             ("opencode-v2", "V2", "opencode")):
    write(Path(slug) / "SETUP.md", f"""# OpenCode {version} exclusive deployment

Generate this variant with `python coding-harnesses/render.py --harness {slug}`.
Merge only this variant's `.opencode/agents` and `.opencode/skills` into the target
project root; merge shared AGENTS instructions once. Do not deploy `{other}` at the
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
""")

write("hermes-agent/config.example.yaml", """# Merge into a chosen Hermes profile/user config, not a project auto-load file.
# Set MATHTRACE_WORKSPACE to the absolute target project path before launching.
skills:
  external_dirs:
    - "${MATHTRACE_WORKSPACE}/coding-harnesses/hermes-agent/skills"
""")

source_lines = ["# Official sources", "", f"Researched {RESEARCH['date']}. Documentation/source inspection only; no live host validation.", "",
                "`research.json` records the precise product identities, findings, source revisions where observed and unresolved features. Links follow upstream default branches unless a revision is explicitly recorded; hosts evolve.", ""]
for harness in RESEARCH["harnesses"]:
    source_lines += [f"## {harness['name']}", "", harness["identity"], ""]
    source_lines += [f"- [{url.split('://', 1)[1]}]({url})" for url in harness["sources"]]
    source_lines += [""]
write("SOURCES.md", "\n".join(source_lines))
