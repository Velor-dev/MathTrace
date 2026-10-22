# Hermes Agent role binding and inline fallback

Native delegation: delegate_task with exact role/packet in its documented goal/context inputs. Children inherit parent toolsets; do not invent a toolsets argument.

No unconfirmed static custom-agent file schema is shipped. The complete existing role definitions are in `coding-harnesses/shared/roles/`; [catalog.json](../catalog.json) lists their names and purposes.

For a supported dynamic delegate, root reads exactly the selected role body and places its full text in the child instruction/prompt input exposed by the host. Append the **complete exported task packet unchanged**, not a summary or selected fields. Keep task_id and packet_hash intact. Use a new context, not a history-inheriting fork. Do not forward the root conversation, other verdicts, campaign/build archives or all skills. Omit model/effort overrides. Request the role's existing single-JSON-object response. Root retains actual returned handles and outputs with honest provenance; this is not a qualified Antigravity capture.

Use only the actual tool schema available in the installed version/profile; this guide does not invent dynamic spawn parameters. If fresh delegation is absent or exposes incompatible context/settings, report that limitation and keep the relevant independent-review gate blocked. For Pi core, delegation is absent by design; an extension would be separately chosen work.

Inline fallback: root may read the selected role prompt and perform explicitly labeled exploration or critique in the current context. Explain that this is root work. Do not label it an independent referee, reproducer, fidelity assessment or adjudication, and do not use it to satisfy independent audit/release/completion requirements. Preserve the original skills' behavior and stopping conditions; do not silently flatten required independent work.

Read [POLICY](../shared/POLICY.md) for the unchanged mathematical and capture limits. Default leaf children inherit parent model/reasoning absent delegation overrides, plus enabled tools and workspace instruction context. Opt-in orchestrators can delegate further when depth allows; MathTrace does not enable this. No model-facing toolsets parameter or static agent discovery is established. GSD-generated agents are not loader evidence. Optional output-schema tolerance does not replace the exact unfenced JSON contract. No capture backend.
