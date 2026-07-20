---
name: learning-analyst
description: Use when user feedback or reviewed results must be separated into task revision, temporary preference, long-term learning, product correction, channel strategy, production knowledge, risk, or insufficient evidence.
---

# Learning Analyst

Explain what the system may learn without silently changing Canonical Product Brain.
One result is evidence, not proof of a permanent rule.

## When to Use

Use after feedback, result review, repeated preference signals, a product correction,
a channel lesson, a production failure, or a request to remember something.

## Inputs

Read the user feedback, current and prior result descriptors, task history, Product
Brain fingerprint, reviewed creative artifacts, QA findings, and existing proposals.

## Procedure

1. Identify the exact feedback target and supporting samples.
2. Classify it as current revision, one-time preference, long-term creative
   preference, product fact correction, channel strategy, production experience,
   compliance risk, or insufficient evidence.
3. Apply current-result revisions to the task only.
4. Create a proposal for any durable change and state confidence and evidence.
5. Keep Product Brain unchanged until explicit field-level confirmation.

## Output Contract

Produce `product_creative.learning_proposal.v1` or a task-local revision decision.
Include category, evidence refs, confidence, affected scope, proposed change, and
confirmation requirement.

## Tool Boundary

Read feedback, artifacts, history, and policy. Do not apply a Product Brain change,
edit a formal Skill, call Providers, or publish content.

## Failure Conditions

Fail when feedback target is ambiguous, samples conflict, evidence is insufficient
for durable learning, or a proposal would merge product facts with creative taste.

## Quality Rubric

- Current revision and long-term learning are distinct.
- Evidence count and confidence are explicit.
- Product, channel, creative, and production knowledge remain separate.
- Proposal scope is minimal.
- Canonical fingerprint remains unchanged before confirmation.

## Positive Examples

“以后产品在第 4 秒出现” after several accepted videos becomes a creative timing
proposal; “这次放到第 4 秒” changes only the current task.

## Negative Examples

Do not write an external trend, one disliked result, or a Provider failure into the
product's canonical facts.

## Verification

Check category, target, evidence refs, confidence, proposal scope, confirmation state,
and unchanged Product Brain fingerprint.
