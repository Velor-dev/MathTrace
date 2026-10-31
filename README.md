# MathTrace

![MathTrace AI reasoning pipeline](assets/mathtrace-banner.png)

**MathTrace** is an AI-powered mathematical problem-solving workflow and formal verification runtime. It combines autonomous multi-agent mathematical reasoning with rigorous, tamper-evident audit trails, native execution with optional Linux sandboxes, and interactive Lean 4 proof checking.

MathTrace structures mathematical inquiry into an immutable, ledger-backed process—ensuring that every theorem, proof obligation, computational step, and counterexample is tracked, verified, and preserved with complete provenance.

---

## Key Capabilities

- **Immutable Transactional Ledger**: All mathematical claims, assumptions, inferences, and campaign events are recorded in an append-only SQLite store with cryptographic SHA-256 state digests.
- **Scoped Evaluation & Cycle Detection**: Inferences are evaluated within strict local scopes using conservative antitone bounds and selected witness forests (`scoped-selected-forest-v3`), preventing circular logic and premature global assertions.
- **Nonparty Adjudication & Challenge Resolution**: Formal objections, refutations, and counterarguments are adjudicated independently by nonparty review protocols, preventing silent substitution of historical audit witnesses.
- **Formal Proof Verification**: Proof code is verified using a pinned official Lean 4 toolchain and checked-target primitive-context replay. Native execution is the default; Linux Bubblewrap is optional. Standalone fresh checks retain `leanchecker --fresh`.
- **Adaptive Frontier Coordination**: Campaigns dynamically project active problem frontiers, track multi-step obligation lineage, and manage committed work intents with crash-resilient, idempotent recovery.
- **Advisory Learning Layer**: Heuristics, proof tactics, and empirical research patterns are curated against verified event lineage to advise reasoning agents without contaminating deductive proof graphs.
- **Native Multi-Agent Roles**: Specialist agent roles (strategists, provers, falsifiers, adjudicators, and formalizers) operate under tool-free, isolated boundaries with attributable terminal transcript recording.

---

## Architecture & Verification Workflow

MathTrace structures mathematical inquiry not as linear text generation, but as a **dialectical multi-agent research and verification runtime**. Constructive reasoning agents formulate lemmas and deductive proofs in parallel with skeptical adversarial agents searching for counterexamples and logical gaps. Claims and refutations are arbitrated by independent nonparty adjudication and verified through Lean 4 primitive kernel execution inside an append-only, tamper-evident ledger.

```mermaid
flowchart TD
    %% Stage 1: Intake & Canonical Ledger
    subgraph S1["1. Mathematical Intake & Canonical Ledger"]
        Problem["Mathematical Problem & Target Contract"] --> Intake["/math-intake & Fidelity Auditor"]
        Intake --> Ledger[("Append-Only Ledger<br/>(SQLite + SHA-256 Digest)")]
    end

    %% Stage 2: Frontier & Multi-Agent Exploration
    subgraph S2["2. Frontier & Dialectical Inquiry"]
        Ledger --> Frontier{"Adaptive Research Frontier<br/>(Lineage & Obligations)"}
        Frontier -->|"Deductive Exploration"| Constructive["Constructive Agents<br/>• Scout (Route & Lemma Discovery)<br/>• Prover (Inference & Deductive Steps)<br/>• Computationalist (Finite Search & Experiments)"]
        Frontier -->|"Skeptical Audit"| Adversarial["Adversarial Agents<br/>• Falsifier (Counterexample Search)<br/>• Referee (Circular Logic & Gap Audit)<br/>• Theorem Checker (Premise & Hypothesis Mapping)"]
    end

    %% Stage 3: Verification & Dispute Adjudication
    subgraph S3["3. Formal Verification & Adjudication"]
        Constructive --> Claims["Candidate Inferences & Lemmas"]
        Adversarial --> Challenge{"Objection or<br/>Counterexample?"}
        Claims -.-> Challenge
        Challenge --"Yes (Dispute)"--> Adjudicator["Nonparty Adjudicator<br/>(Substantive Evidence Trial)"]
        Adjudicator --"Valid Objection"--> Frontier
        Challenge --"No (Cleared)"--> Formalizer["Lean 4 Formalizer & Kernel<br/>(Primitive Replay in Isolated Sandbox)"]
    end

    %% Stage 4: Candidate Freeze & Release
    subgraph S4["4. Freeze, Audit & Release"]
        Formalizer --> Freeze["Frozen Candidate<br/>(Immutable Proof Manifest)"]
        Freeze --> Audit["Multi-Dimensional Audit<br/>(Fidelity, Closure & Nonparty Clearance)"]
        Audit --> Release["Release Receipt<br/>(Cryptographically Pinned Theorem)"]
        Audit -.-> Advisory["Advisory Learning Layer<br/>(Curated Strategy Heuristics)"]
    end

    %% Styling
    classDef default fill:#1e1e2e,stroke:#45475a,stroke-width:1px,color:#cdd6f4;
    classDef highlight fill:#181825,stroke:#89b4fa,stroke-width:2px,color:#89b4fa;
    classDef alert fill:#31202b,stroke:#f38ba8,stroke-width:1.5px,color:#f38ba8;
    classDef success fill:#1c2d27,stroke:#a6e3a1,stroke-width:1.5px,color:#a6e3a1;
    classDef ledger fill:#1e1e2e,stroke:#f9e2af,stroke-width:1.5px,color:#f9e2af;

    class Ledger ledger;
    class Frontier,Challenge highlight;
    class Adversarial,Adjudicator alert;
    class Constructive,Formalizer success;
    class Release success;
```

### Architectural Stages

1. **Intake & Canonical Ledger**: Problem statements, variable domains, and exact completion criteria (proof vs. refutation) are formalized. The `Fidelity Auditor` validates that machine-checkable targets faithfully reflect original requirements. All events are recorded in an append-only SQLite ledger with SHA-256 state digests.
2. **Dialectical Inquiry**: The campaign manager projects an adaptive frontier of subgoals and obligations. Dual autonomous agent tracks operate simultaneously:
   - **Constructive Track**: `Scout` charts viable proof routes, `Prover` constructs deductive lemmas and discharges assumptions, and `Computationalist` runs bounded numerical experiments.
   - **Adversarial Track**: `Falsifier` aggressively tests domain boundaries for counterexamples, `Referee` detects hidden circular dependencies, and `Theorem Checker` verifies applicability of external references.
3. **Formal Verification & Adjudication**: When disputes or counterexamples emerge, an independent `Adjudicator` evaluates substantive mathematical merit (majority voting is strictly prohibited). Cleared arguments are compiled by `Formalizer` and replayed against a fresh Lean 4 kernel inside an isolated execution environment.
4. **Candidate Freeze & Release**: Complete solutions are permanently frozen into an immutable dependency manifest. After passing a multi-dimensional audit (full proof coverage, target fidelity, dependency closure, and unadjudicated challenge clearance), a cryptographically verifiable `Release Receipt` is issued. Successful proof tactics and failure patterns are curated into the `Advisory Learning Layer` for future campaigns without contaminating deductive trees.

---

## Repository Structure

```text
MathTrace/
├── mathtrace/             # Core Python runtime, CLI, and Lean semantic inspector
├── tests/                 # Comprehensive regression test suite
├── tools/                 # Developer setup, package validation, and native installers
├── docs/                  # Operational guides, workspace map, and architectural decisions
│   ├── README.md          # Detailed repository navigation guide
│   ├── architecture/      # Authoritative architectural records and review dispositions
│   ├── coordination.md    # Adaptive frontier and obligation tracking
│   ├── evaluation.md      # Scoped support, refutations, and witness forests
│   ├── evidence.md        # Computational receipts and formal checking boundaries
│   ├── execution.md       # Durable intent, sandbox isolation, and recovery
│   ├── native-capture.md  # Terminal observation and host attribution limits
│   ├── completion.md      # Criteria fulfillment and stopping criteria
│   └── learning.md        # Advisory extraction, curation, and target admission
├── openspec/              # OpenSpec specifications, changes, and configuration
├── coding-harnesses/      # Agent harness definitions for supported environments
└── work/                  # Local validation runs, toolchains, and recovery archives (not committed)
```

---

## Requirements and Prerequisites

- **Python**: Version 3.11 or newer.
- **Operating System**: Windows, Linux or macOS. Native execution requires no WSL or container.
- **Optional Execution Sandbox**: Select `execution_mode: "bubblewrap"` explicitly to use Linux Bubblewrap and `libseccomp`, including the existing Windows/Ubuntu WSL transport.
- **Interactive Theorem Prover**: Pinned Lean v4.30.0 toolchain (provisioned by the `install_lean` runtime operation).

---

## Getting Started

### 1. Installation

Install into your project with Node 22+ and Python 3.11+:

```bash
npx mathtrace@latest
```

Select your installed coding harness from the numbered menu. MathTrace installs
its runtime and integration inside the current project. See [installation](docs/installation.md)
for prerequisites, supported hosts, optional execution isolation, and safe updates.

Install MathTrace in development mode or as a standalone wheel:

```bash
# Clone or navigate to the repository
cd MathTrace

# Install Python package in editable mode
pip install -e .
```

Only when choosing optional Bubblewrap execution, provision its Linux or WSL environment:

```bash
python tools/setup_execution.py
```

### 2. Command-Line Interface

The MathTrace CLI provides a unified control surface for campaign administration:

```bash
# Display CLI identity and available commands
python -m mathtrace identity
python -m mathtrace --help

# Initialize a new mathematical campaign database
python -m mathtrace init --db .math/state.sqlite

# Check campaign database health and state digest
python -m mathtrace health --db .math/state.sqlite

# Export a state snapshot
python -m mathtrace snapshot --db .math/state.sqlite
```

#### Registering a Mathematical Contract

Create a JSON contract definition (e.g., `contract.json`):

```json
{
  "statement": "For every positive real x, x squared is positive.",
  "definitions": [],
  "completion": "An exact proof or a domain-valid counterexample."
}
```

Register the contract into the campaign ledger:

```bash
python -m mathtrace contract --db .math/state.sqlite --input contract.json
```

The CLI returns an immutable contract identifier used for downstream claim registration, inference submission, and candidate auditing.

### 3. Interactive Agent Workflows

MathTrace equips AI agents and human researchers with specialized skills:

- **`/mathtrace-help`**: Interactive discovery guide explaining workflows, specialist roles, and research phases.
- **`/math-intake`**: Formalizes problem statements, definitions, and completion contracts.
- **`/math-research`**: Explores lemmas, candidate proof branches, and computational experiments.
- **`/math-formalize`**: Translates informal arguments into verified Lean 4 declarations.
- **`/math-audit`**: Runs multi-dimensional audits on frozen solution candidates.
- **`/math-release`**: Finalizes audited solutions and issues release receipts.

To update or synchronize the local agent environment in `.agents/`:

```bash
python tools/install_native.py
```

---

## Verification and Testing

MathTrace includes a comprehensive test suite covering database transactions, cycle detection, witness forest memoization, Lean checking integration, and host capture isolation:

```bash
# Run full deterministic test suite
pytest tests

# Build and validate isolated package wheel
python tools/validate_package.py

# Validate OpenSpec specifications and changes
openspec validate --all
```

---

## Development and Specifications

Project maintenance and feature development are governed strictly through **OpenSpec**. System requirements and verified capability behaviors are documented under:

```text
openspec/specs/
```

Before proposing changes, review the coding agent instructions in [AGENTS.md](AGENTS.md) and the operational guides in [docs/](docs/).

---

## Copyright and Licensing

Copyright © 2026 Velor-dev. Public project author/developer: [Velor-dev](https://github.com/Velor-dev).

MathTrace is proprietary and source-available, with free personal, academic,
and commercial use under [LICENSE](LICENSE). The license permits installation
and necessary project-local/internal operational copies, while reserving general
modification and redistribution rights. The separate OpenSpec development-skill notice is included in [LICENSE](LICENSE).

When publishing your own project, exclude installed MathTrace software assets
(including its runtime, skills, agents, and copied guides) and direct users to
install the official distribution. Your original research, proofs, results, and
project files are not restricted merely because you used MathTrace. Do not
remove your own shared instruction files; exclude only copied MathTrace material
from public redistribution. These permissions do not override third-party terms.

The official npm package is `mathtrace`. Publication requires an assembled,
integrity-verified payload; package publication does not create a GitHub release.
