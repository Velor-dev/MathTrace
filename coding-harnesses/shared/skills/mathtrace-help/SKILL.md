---
name: mathtrace-help
description: "Explain the MathTrace skills and when to use them; show the workflow help guide"
---

<objective>
Display the MathTrace skill reference so the user can understand the skills and choose the appropriate workflow. Output only the guide's reference content, without project-specific analysis, status inspection or additional next-step suggestions.
</objective>

<execution_context>
@coding-harnesses/shared/help.md
</execution_context>

<process>
Read [help.md](../../help.md), then display the content inside its `<reference>` block. This is a help request: do not initialize or inspect a campaign, dispatch workers, execute checking, or invoke another skill merely to show help.
</process>
