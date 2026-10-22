# Project installation and release validation

The npm installer is prepared and tested locally; this checkout does not publish it.
Python 3.11+ with working `venv`/pip and Node 22+ are prerequisites. Python is never
installed automatically. MathTrace proprietary free-use terms are supplied in LICENSE; separate third-party terms remain intact.

`python tools/validate_package.py` builds from a fresh allowlisted source tree and
checks the complete wheel, metadata, entry points, RECORD hashes and unchanged
LICENSE. Historical builds are retained; they cannot contaminate this build.

## Preparing and running the local npm artifact

Run `python tools/build_npm.py`; it reports a package directory under
`work/validation/npm/`. In that directory run `npm pack --ignore-scripts`.
The private package can be extracted and its `bin/install.cjs` executed with Node
in a separate target project. Registry publication is neither performed nor needed.
The eventual distribution entry point is `npx mathtrace@latest`; this checkout
does not grant publication permission or introduce licensing terms.

Use `--harness <id>` for automation, `--python <executable>` for a specific existing
Python, and `--execution-mode bubblewrap` only for explicit optional sandbox
provisioning. The default is Direct Execution; it does not probe WSL or Bubblewrap.
Bubblewrap/Linux or Windows/Ubuntu WSL and libseccomp must already be prepared.
Runtime operation JSON still explicitly selects Bubblewrap; the installer does
not silently change runtime defaults or prior attempts.

## Project and external prerequisites

Host applications must already be installed and their version command accessible.
Use `--host-executable <path>` when the installed host uses a different executable
name or is outside PATH; the same version and prerequisite checks still apply.
The installer checks only documented static requirements, not authentication,
effective tool isolation, model settings or qualification for independent evidence.
Pi requires the reviewed upstream subagent extension's index.ts and agents.ts;
unknown extension revisions stop for compatibility review. Hermes must already
include the project's `coding-harnesses/hermes-agent/skills` in skills.external_dirs
in the chosen HERMES_HOME/config.yaml (or the default profile). JSON-compatible
YAML or the documented simple YAML list is checked without a parser dependency.
The MATHTRACE_WORKSPACE binding must be set when used. Complex YAML that cannot be
verified stops with instructions. No profile, extension, credential or global host
configuration is changed. Rerun after preparing external prerequisites.

## Owned files and recovery

The installer uses `.mathtrace/` for a private versioned environment, launcher,
receipt, temporary files and deployment journal. Existing `.venv`, package.json,
host settings and unrelated skills are preserved. The launcher is
`node .mathtrace/run.cjs <existing-operation>`; it needs no activation or PATH edit.
Project-local root instructions use that launcher. Worker role bodies remain exact.

The default `.math/state.sqlite` is initialized only when absent. Existing valid
state is reused. The pinned official Lean release is provisioned through existing
MathTrace mechanisms; matching complete verified toolchains are reused. Setup
creates no mathematical contract or accepted proof. Provisioning can append valid
records before a later file-deployment failure; these are retained and reconciled
on retry, never rolled back by restoring a campaign database.

Preflight stops on edited owned files or different unowned files. Identical
unowned files remain unowned. Only a delimited MathTrace section in AGENTS.md is
managed; surrounding user instructions are preserved. Updates retain older runtime
environments and toolchains for historical provenance. No automatic cleanup is run.
Switching harnesses requires explicit manual reconciliation. Codex uses existing
unambiguous skill locations; fresh projects default to `.codex/skills`. Use
`--codex-skills .agents/skills` only when compatible. Same-name duplicate locations
and existing native ownership stop safely; paired TOML/Markdown agents are retained.

Ordinary deployment failure restores touched files. An interrupted process can
leave `.mathtrace/install.lock`: first verify that the recorded installer process
has stopped, then remove only that lock and rerun. Recovery checks the entire
journal before restoring files; if subsequent user edits conflict, preserve them
and inspect `.mathtrace/journal.json` before manual reconciliation. The installer
does not overwrite those edits to complete recovery. A moved project or missing
base Python requires recreating its private runtime by reinstalling.

## Attribution and license

Project-local installation retains LICENSE under `.mathtrace/docs/`; these remain available without
the source checkout or npm cache. MathTrace is proprietary, with free personal,
academic, and commercial use and necessary operational copying under LICENSE.
Exclude installed MathTrace software assets from public project releases and
have users reinstall the official distribution. Preserve your own project files
and root license. Package preparation does not authorize publication; the npm
private flag and rejecting publication hook remain enabled.

Updates remove obsolete MathTrace notice copies only when unchanged and previously
owned. Edited or unowned conflicts are reported and preserved. Source-repository
third-party attribution and the OpenSpec MIT license text are retained in README.md;
Lean distributions retain their own LICENSE and LICENSES files.
