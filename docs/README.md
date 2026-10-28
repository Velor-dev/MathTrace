# MathTrace Workspace Map

This is the directory and file-placement guide for MathTrace. For development changes and governance, read [AGENTS.md](../AGENTS.md) and use the [OpenSpec specifications](../openspec/specs/). For a mathematical campaign, use the owned [root protocol](../.agents/math/PROTOCOL.md) and that campaign's `.math` state. For choosing an interactive skill, read the generated [skill guide](../.agents/math/help.md).

## Where to Look and Write

| Location | Owner and contents | Purpose / When to use |
|---|---|---|
| `mathtrace/` | Authoritative Python runtime, CLI, and Lean helper; `pyproject.toml` owns packaging/CLI entry configuration | Changing runtime implementation. |
| `tests/` | Developer regression tests and explicit fixtures | Checking changed runtime invariants and regression coverage. |
| `tools/` | Developer installation, setup, and validation helpers | Running package validation, native projection installation, and toolchain checks. |
| `docs/` | Operational guides, workspace map, and architectural decisions | Documenting system behavior, operations, and historical decisions. |
| `openspec/` | OpenSpec specifications (`specs/`), change proposals (`changes/`), and configuration | Specifying system capabilities and managing project changes via OpenSpec. |
| `.agents/` | Generated native roles, skills, protocol/help/config and OpenSpec skills | Generated and managed via `tools/install_native.py`; preserves OpenSpec skills and workflows. |
| `.math/` | Per-campaign immutable records/events and derived current eligibility | Running mathematical research through the runtime; created when a campaign is initialized. |
| `work/validation/` | Retained observations, fixtures, exact receipts, and local checking environments | Storing validation runs and checking environments. |
| `work/archives/` | Managed projection recovery snapshots | Storing verified native projection backups created by the installer. |
| `work/provenance/` | Historical comparison and provenance material | Preserving upstream source provenance. |
| `build/`, `*.egg-info/`, `.pytest_cache/`, `__pycache__/` | Generated build copies, metadata, and caches | Temporary build and test caches created by tools. |

`AGENTS.md` owns development governance. `openspec/` owns all capability specifications and change workflows. Historical architectural decisions and review dispositions are preserved in [docs/architecture/decisions.md](architecture/decisions.md).

## Operational Documents

| Guide | Scope |
|---|---|
| [Coordination](coordination.md) | Adaptive frontier, work intents, route/obligation lineage, terminal intake |
| [Evaluation](evaluation.md) | Scoped support/refutation, assumptions, selected witnesses, and currentness |
| [Evidence](evidence.md) | Computation/Lean plans, actual receipts, compiled fidelity, and assurance limits |
| [Execution](execution.md) | Durable intent, observed completion, recovery, and explicit reruns |
| [Native capture](native-capture.md) | Native attribution, exact input admission, and host limits |
| [Completion](completion.md) | Exact requested outputs, fulfillment/delivery, and retained negative reports |
| [Learning](learning.md) | Local advisory extraction, curation, target admission, and revocation |
| [Decisions](architecture/decisions.md) | Preserved historical architectural decisions, sibling audits, and assurance bounds |

## Developer Tools

Run from the workspace root; read each helper's scope before executing it:

| Helper | Purpose and effects |
|---|---|
| `tools/install_native.py` | Verify ownership, archive previous projection, regenerate `.agents/` preserving external skills, and update `work/native-install.json` |
| `tools/validate_package.py` | Build and install an isolated wheel, verify source/helper bytes and CLI identity, retaining packaging evidence |
| `tools/setup_execution.py` | Provision the optional pinned Linux isolation backend (Bubblewrap); native execution needs no sandbox setup |
| `tools/validate_lean.py` | Explicit Lean boundary fixtures against the provisioned validation database |
| `tools/validate_canonical_formal.py` | Isolated ordinary-module receipt and invalidation fixtures |
| `tools/probe_compiled_semantics.py` | Specialized unmocked semantic-channel prototype evidence |

## Local commit checks

Install the locked development-only Ruff tool with existing uv:

```sh
uv sync --locked --only-group quality --inexact
git config --local core.hooksPath .githooks
```

The pre-commit hook checks only staged added/modified/renamed Python files,
using their staged contents and staged pyproject.toml. Deleted files and
non-Python-only commits do not run Ruff. Merge conflicts fail the check.
Ruff lint uses E4/E7/E9/F (basic errors and Pyflakes), followed by format --check.
No files or staged bytes are fixed automatically. Partially staged changes are
preserved. Existing files are not reformatted in bulk; changed Python files must
pass the configured checks when committed.

Checks run offline with the installed tool and the existing uv.lock authority.
The installed Ruff version must match the staged lockfile; mismatches fail closed.
No LLM, GitHub Actions, full tests, Lean provisioning, or npm checks run on commit.
A missing local environment/tool fails with an error; rerun the setup command.
The inexact setup keeps other already-installed developer tools, including pytest.
Install uv separately if it is unavailable. The repository-owned pre-commit
file must retain its executable Git mode when committed (including from Windows). Other clones must opt in using the
commands above. No pre-push hook is installed. To disable this local setting:

```sh
git config --local --unset core.hooksPath
```

To fix only specific files, review and run Ruff manually before staging:

```sh
uv run --locked --offline --no-sync --group quality ruff check path/to/file.py
uv run --locked --offline --no-sync --group quality ruff format path/to/file.py
```

The existing full regression, package, npm, and OpenSpec checks remain separate.
