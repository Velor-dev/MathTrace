# PrimeAgent role binding and inline fallback

Native delegation: Documented rlm.spawn(...) creates dynamic children via the Python REPL. Root supplies the exact role and packet through the live exposed schema; no guessed arguments or .prime/agents definitions.

No unconfirmed static custom-agent file schema is shipped. The complete existing role definitions are in `coding-harnesses/shared/roles/`; [catalog.json](../catalog.json) lists their names and purposes.

For a supported dynamic delegate, root reads exactly the selected role body and places its full text in the child instruction/prompt input exposed by the host. Append the **complete exported task packet unchanged**, not a summary or selected fields. Keep task_id and packet_hash intact. Use a new context, not a history-inheriting fork. Do not forward the root conversation, other verdicts, campaign/build archives or all skills. Omit model/effort overrides. Request the role's existing single-JSON-object response. Root retains actual returned handles and outputs with honest provenance; this is not a qualified Antigravity capture.

Use only the actual tool schema available in the installed version/profile; this guide does not invent dynamic spawn parameters. If fresh delegation is absent or exposes incompatible context/settings, report that limitation and keep the relevant independent-review gate blocked. For Pi core, delegation is absent by design; an extension would be separately chosen work.

Inline fallback: root may read the selected role prompt and perform explicitly labeled exploration or critique in the current context. Explain that this is root work. Do not label it an independent referee, reproducer, fidelity assessment or adjudication, and do not use it to satisfy independent audit/release/completion requirements. Preserve the original skills' behavior and stopping conditions; do not silently flatten required independent work.

Read [POLICY](../shared/POLICY.md) for the unchanged mathematical and capture limits. The audited Rust child host inherits parent model identity and thinking when no override is requested. Effective tools/context and producer-bound admission remain unvalidated; spawn returns an admission handle before completion. Older TypeScript package guides do not describe this tree. No capture backend.
