# Pi official subagent extension setup

Verified 2026-10-15 against the official [extension guide](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/examples/extensions/subagent/README.md), [agent loader](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/examples/extensions/subagent/agents.ts) and [implementation](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/examples/extensions/subagent/index.ts). This adapter requires that extension; Pi core alone does not supply its `subagent` tool.

## Deployment

The project-local npm installer checks this existing external extension before
deploying project files. It does not install or update it. Prepare a compatible
reviewed revision of both files externally, then rerun installation; unknown
revisions stop for review rather than silently acquiring a new dependency.

Use a compatible Pi checkout containing `packages/coding-agent/examples/extensions/subagent/`. Follow its installation instructions to link `index.ts` **and** `agents.ts` into `~/.pi/agent/extensions/subagent/`, retaining their sibling layout. On Windows, copying both files to that directory is an alternative to creating symlinks. Match extension and installed Pi versions, including the extension's package imports. This payload does not vendor, install, modify or launch the upstream extension.

Merge this payload's `.pi/agents/` and `.pi/skills/` into the target project's corresponding directories. Keep `coding-harnesses/shared/` available and merge the shared project instruction section into the existing `AGENTS.md` once. Do not install the example coding agents, model choices or workflow prompt presets: use the eleven existing `math-*` roles supplied here. Start Pi from the target project root, outside this staging directory.

## Extension binding

Project agents are Markdown files at `.pi/agents/*.md`. Their frontmatter supplies `name` and `description`; the body is the full existing MathTrace role prompt. The extension finds the nearest project agent directory. Each MathTrace call uses `agentScope: "project"`. The default `"user"` scope does not load these agents; `"both"` combines directories, with project definitions taking precedence. Leave `confirmProjectAgents` at its default; interactive untrusted projects receive the extension's confirmation.

The root delegates through the extension's `subagent` tool. A single call has this shape; the placeholder must be replaced with the **complete exact exported packet**, unchanged:

```json
{
  "agent": "math-referee",
  "task": "<complete exported task packet JSON>",
  "agentScope": "project"
}
```

Choose the appropriate existing role and task; this example adds no mandatory referee step. Role bodies already specify the exact single-JSON response. Root retains actual output and provenance, handles failures/context requests, and mediates all execution and canonical changes under the existing protocol. Do not forward root conversation, other verdicts or campaign/build history to blind tasks.

The extension supports `tasks: [{agent, task}, ...]` for parallel delegation and `chain: [{agent, task}, ...]` for sequential delegation. Supply exactly one mode per call. Parallel dispatch is appropriate only for the existing independent tasks selected by the protocol, each with its own complete packet. The implementation limits a batch to eight tasks, four concurrent, and caps model-visible parallel output at 50 KB per task; retrieve full tool details before assessing an incomplete response.

Chains can substitute `{previous}` with the preceding output. Do not use that substitution for blind workers or mutate exact packets through it. Sequential mathematical follow-up remains root-mediated: root assesses prior output and prepares the next exact task normally. No sample coding chains, new phases, slash commands or automatic role roster are added.

## Inheritance and boundaries

The supplied agent definitions omit `model` and any thinking override. The extension reads the dispatching session's active model and thinking level and passes them to each separate Pi process when the agent has no model override. No MathTrace routing or setting change is introduced.

The inspected loader turns an empty tool list into an undefined list, and the launcher only sends `--tools` for a nonempty list. Therefore these definitions omit `tools` rather than falsely claiming `tools: []` disables tools. The unchanged role bodies assign tool-free work, prohibit delegation and require reporting unexpected access; this is a prompt policy. Default tools, extensions and project/bootstrap context may remain available. The launcher appends the role prompt to the child system prompt and uses the working directory; a fresh process alone does not establish mathematical blindness or enforced read isolation.

No Pi capture/admission backend is added. Returned outputs cannot bypass existing independent-review, audit, release or fulfillment gates. If the extension is unavailable, report the missing dependency and keep required delegation blocked; do not silently substitute inline-only review. See [shared policy](../shared/POLICY.md) for the unchanged assurance boundary.
