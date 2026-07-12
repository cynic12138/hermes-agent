---
name: product-creative-operator
description: Operate the Product Creative plugin through Hermes conversation by using product_workflow_run as the primary natural-language workflow entry.
version: 0.1.0
author: product_creative
---

# Product Creative Operator

Use this skill when a user asks Hermes to work on a product-centered creative workflow: product understanding, Product Brain, material assets, ecommerce copy, Xiaohongshu copy, Douyin scripts, image briefs, video briefs, or iterative feedback.

## Primary Tool

Prefer `product_workflow_run` as the main entry point.

If the user names a product but does not provide a local `product_id`, call `product_workspace_resolve` first. Do not invent a product id from the visible product name. Create a new workspace only when the user clearly asks to start a new product.

Use it when the user asks to:

- create or continue a product workspace
- ingest product text or image/material information
- generate channel copy
- generate image briefs or video briefs
- revise content using feedback
- continue the next Product Creative workflow step

For live video generation, keep this order:

1. resolve or create the product workspace
2. read Product Brain and material library through `product_workflow_run`
3. create and review the video brief
4. confirm or revise the video brief before provider payload generation
5. build the video provider payload
6. check video reference readiness
7. check video live readiness
8. ask for explicit confirmation and create the video execution policy
9. ask for explicit confirmation before submitting the live video task
10. query video task status or import the provider result URL
11. record user feedback on the generated video result
12. create/apply Product Brain evolution only after explicit user confirmation

## Operating Rules

- Ground every generation in the current Product Brain and material library.
- Keep products isolated; do not reuse facts from a demo product for a new product.
- Stop at guard boundaries instead of mutating Product Brain automatically.
- Ask for confirmation before live external provider calls.
- Ask for confirmation before creating a live video execution policy; this policy is the spending/execution boundary.
- Treat generated artifacts as reviewable outputs, not product truth.
- Treat provider result URLs and downloaded videos as generated results, not Product Brain facts.
- If the user provides a local image path, register or analyze it through the workflow before relying on its content.
- Prefer `user_next_message` in tool results when explaining the next step to the user.
- Keep `developer_command` or `command` as diagnostics only; do not present scripts as the normal product flow.

## Response Style

After tool execution, explain:

- what workflow step ran
- what artifact or review package was created
- whether the system stopped for confirmation
- what the user can review or say next

Do not tell the user to run `product_creative.ps1` as the normal product flow.
