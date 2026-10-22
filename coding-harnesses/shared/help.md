<reference>
This is the existing MathTrace skill guide. Skill names and behavior are unchanged; native invocation syntax and delegation capabilities vary by harness. For these packaged ports, consult the selected harness README and [adapter binding](POLICY.md). The existing native qualification described below belongs to the Antigravity capture profile; the other adapters do not add capture backends or independently qualify their outputs.

# MathTrace Skill Guide

MathTrace supports mathematical research with exact problem statements, independent assessment and durable evidence. Skills guide the root agent's work; they are not fixed phases that every problem must follow. Research can branch, return to an earlier question or preserve a useful partial result.

## Quick start

1. Use `/math-intake` with the original problem, definitions and what would count as a satisfactory result.
2. Use `/math-research` to explore proofs, counterexamples and outstanding obligations.
3. Use `/math-progress` whenever you want to understand the current evidence or resume existing work.

When an argument is ready, `/math-audit` challenges its exact frozen evidence. Use `/math-formalize` when formal checking is appropriate, and `/math-release` only when the requested result and its audit are currently supported. `/math-capture` preserves partial discoveries and local lessons throughout research.

Invoke a skill by its name in the host's skill picker or use the slash form shown here. Follow it with an ordinary request; these examples do not introduce command-line flags. `/mathtrace-help` displays this guide without opening or changing a campaign.

## Choose a skill

| Skill | Use it when you want to… |
|---|---|
| `/mathtrace-help` | Understand the available skills and choose one. |
| `/math-intake` | Turn an original problem into an exact research contract and requested outputs. |
| `/math-research` | Explore, prove, falsify or continue unresolved mathematical work. |
| `/math-audit` | Freeze and independently challenge a specific candidate argument. |
| `/math-formalize` | Propose a formal proof and obtain actual checking evidence. |
| `/math-release` | Release an exact result only after current support and audit gates pass. |
| `/math-progress` | Inspect evidence, blockers, fulfillment and unfinished attempts, or diagnose resumption. |
| `/math-capture` | Preserve claims, counterexamples, failed routes, partial results and local advisory lessons. |

## Skills in detail

### /mathtrace-help — understand the workflow

Use this for an overview or a reminder of which skill fits your intent. It reads this guide and displays the reference; it does not inspect project status, create campaign records or launch research. No campaign database is needed.

Example: `/mathtrace-help`

### /math-intake — state the exact request

Provide the original problem, definitions, domains, assumptions, permitted foundations and completion criteria. Include any required proof method, algorithm, assurance or delivery requirement.

The root preserves the source problem, registers its contract and target claims, and maps the entire request to exact required outputs. That mapping needs independent assessment and explicit activation. Missing criteria remain unresolved; an easier lemma does not replace the original target.

Example: `/math-intake Investigate this statement for every positive integer n. Preserve the attached definitions; I want a proof or a domain-valid counterexample.`

### /math-research — advance unresolved mathematics

Provide the active target or describe the question you want to pursue. For existing work, use its exact campaign records rather than rephrasing the problem from memory.

The root reconciles blockers and chooses adaptive work: independent exploration, proof construction, falsification, theorem applicability, context requests or mediated experiments. Proposals and residual obligations are preserved without automatic acceptance. Multiple routes can remain open; finding a gap in one argument does not refute the claim.

Further exploration is optional once the active request's mathematics meets its required assurance. Requested delivery and observation of already-started attempts may still remain. Fulfillment does not mean research exhaustion.

Example: `/math-research Continue the active target. Look for a counterexample as well as a proof, and preserve any unproved reductions.`

### /math-audit — challenge an exact candidate

Provide the candidate argument and its supporting records. This is appropriate when there is an actual proof or disproof to assess; open-ended discovery belongs to research.

The root freezes the exact evidence and selected dependencies, then commissions independent proof or refutation, target-fidelity, dependency and falsification assessments. Applicable objections require substantive adjudication. A valid fatal objection is not outvoted by passing reviews. An alternative argument cannot silently replace evidence beneath a frozen audit.

Example: `/math-audit Audit this candidate against the original target, including every assumption and cited theorem application.`

### /math-formalize — obtain formal checking evidence

Provide the exact claim or candidate, its assumptions and foundations, and the intended formal target. A formalizer proposes source; the root separately reviews and runs the checker when the required environment is available.

The result is proposed formal source or an actual checking receipt with its limits. Unexecuted code is not a checked proof. MathTrace currently supports pinned Lean v4.30.0 same-kernel checking. Independent assessment must still establish that the represented theorem faithfully matches the original problem. Independent-kernel checking and source-to-object correspondence are not supplied by that label.

Example: `/math-formalize Formalize this exact lemma in Lean and record what was actually checked, including the mapping to the original statement.`

### /math-release — deliver a currently supported result

Provide the exact audited candidate and requested assurance. The root rechecks its selected support, audit witnesses, target fidelity, required formal receipts and applicable objections before using the release gate. Missing gates remain unmet.

A release records the exact result and its assurance; it does not make arbitrary mathematics true or silently upgrade an informal assessment to machine checking. Later evidence can withdraw current eligibility while historical decisions remain intact. This skill does not itself authorize publishing to an external service.

Example: `/math-release Release the exact audited candidate at the assurance required by the active request, reporting any remaining limitation.`

### /math-progress — inspect, resume or diagnose

Provide the campaign or target you want inspected and, if helpful, the uncertainty you want explained. The root uses health, progress and target-frontier queries to distinguish current evidence from historical status.

Expect an account of support, blockers, requested fulfillment, delivery, unresolved attempts and available next work. A task's completion or an old accepted event does not establish current mathematical validity. Missing terminal evidence requires inspection or collection, not automatic retry. This skill is the starting point for understanding an interrupted campaign; `/math-research` advances the resulting mathematical work.

Example: `/math-progress Explain where the active campaign stands, what remains required, and which attempts still need observation.`

### /math-capture — preserve discoveries and lessons

Provide the exact claim, counterexample, partial result, failed route or observation worth preserving, together with its evidence and unresolved conditions.

Mathematical proposals retain their normal assessment gates. Local learning follows a separate advisory path: select an exact event/outcome boundary, extract a lesson, explicitly curate or decline it, then admit current advice to an exact informed target. Changed evidence or revoked admission can make advice stale. Blind workers receive no automatic portfolio or lesson history.

Captured advice is not a proof premise, acceptance decision or cross-project global memory. Correctness-critical content needs explicit mathematical evidence or task obligations.

Example: `/math-capture Preserve this failed reduction, its exact obstruction and reopening condition as a local lesson for the active target.`

## Common research situations

| Situation | Suitable path |
|---|---|
| A new mathematical problem | Intake, then research on its exact targets. |
| Returning after a break | Progress to inspect current state, then research on the unresolved work. |
| A promising argument | Audit its frozen evidence; revise through explicit new evidence if needed. |
| A formal proof is required | Formalize, assess the checked target's fidelity and audit the resulting candidate before release. |
| A route failed or only a lemma was proved | Capture the exact partial result or failure; preserve remaining obligations and explore alternatives. |
| The requested mathematics is sufficient | Inspect fulfillment and delivery; release if required and eligible. Further exploration is optional. |

These are examples, not a mandatory sequence. Formalization and exploration may alternate, and an objection can reopen a previously supported result.

## Files and deeper guidance

- `.math/state.sqlite` holds a mathematical campaign's immutable evidence and decisions. Current queries distinguish usable support from historical events.
- [PROTOCOL.md](PROTOCOL.md) defines the root's execution contract. Operational skills follow it; help only displays this reference.
- The shared skill instructions are [intake](skills/math-intake/SKILL.md), [research](skills/math-research/SKILL.md), [audit](skills/math-audit/SKILL.md), [formalize](skills/math-formalize/SKILL.md), [release](skills/math-release/SKILL.md), [progress](skills/math-progress/SKILL.md), [capture](skills/math-capture/SKILL.md) and [help](skills/mathtrace-help/SKILL.md).
- In the source checkout, [coordination](../../docs/coordination.md), [completion](../../docs/completion.md), [evidence](../../docs/evidence.md), [execution](../../docs/execution.md), [evaluation](../../docs/evaluation.md), [learning](../../docs/learning.md) and [native capture](../../docs/native-capture.md) explain detailed operations and assurance limits. `python -m mathtrace --help` lists the local runtime operations; skills are agent workflows rather than CLI subcommands.
- In the source checkout, root `AGENTS.md` governs development. Development records are separate from campaign mathematics and are not blind-worker input. Runtime skills do not require development tooling.

The user selects the root model and reasoning effort; native siblings inherit both by default. MathTrace applies no automatic model/effort routing or overrides. A different subagent model is a manual user configuration choice.

Workers receive exact packets and an assigned tool-free policy; root mediates computation and canonical commits. Supported native qualification binds exact recorded inputs and no recorded tool use. Residual platform controls remain callable; stronger host isolation and statistically independent errors are not established. These limits do not turn benign global platform-guide skills into contamination by mere presence.
</reference>
