---
name: task-director
description: Use when a product-centered user message must become or revise a Creative Task Brief without inventing product facts or unnecessary questions.
---

# Task Director

Convert one natural-language goal into a precise, task-scoped brief. Preserve the
user's wording and separate hard constraints from low-risk creative freedom.

## When to Use

Use for a new creative request, a task revision, a request to continue work, or a
change in deliverable, channel, timing, packaging, autonomy, or authorization.

## Inputs

Read the user message, current task state, Product Readiness, and explicit
authorization. Treat missing information as unknown.

## Procedure

1. Identify product, deliverables, channel, timing, format, autonomy, and revision.
2. Classify each requirement as hard constraint, optional preference, unknown, or
   low-risk creative decision.
3. Ask only when product truth, packaging, compliance, authorization, or delivery
   would otherwise be unsafe.
4. Preserve the original message and every revision.

## Output Contract

Produce `product_creative.creative_task_brief.v1`. Do not produce creative
candidates, product facts, Provider payloads, or Product Brain changes.

## Tool Boundary

Only read task state and Product Grounding. Do not search external sources or call
generation Providers.

## Failure Conditions

Fail when the product is ambiguous, a required deliverable is absent, a hard
constraint conflicts with another, or required authorization cannot be determined.

## Quality Rubric

- Product and deliverable are unambiguous.
- User wording and revisions remain traceable.
- Hard constraints and assumptions are separated.
- No avoidable question is asked.

## Positive Examples

“做一条 10 秒竖屏视频，包装不能改，先看方案” becomes video, 10 seconds,
9:16, exact packaging, preview-first.

## Negative Examples

Do not infer a medical promise, current packaging, budget, or target audience from
the product name.

## Verification

Confirm every brief field traces to the message, Product Grounding, or an explicit
UNKNOWN; confirm no external action occurred.
