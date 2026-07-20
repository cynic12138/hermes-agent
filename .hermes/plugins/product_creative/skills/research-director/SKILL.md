---
name: research-director
description: Use when a Creative Task needs current Web, Xiaohongshu, Douyin, workspace, or historical evidence converted into source-specific creative insight.
---

# Research Director

Turn collected sources into traceable creative observations. Keep external material
outside Product Brain and never collapse different platforms into one generic summary.

## When to Use

Use when the task requests current inspiration, channel references, trend context,
competitor signals, user language, hook analysis, or historical comparison.

## Inputs

Read the Creative Task Brief, Product Grounding Pack, task-scoped source snapshots,
and prior reviewed creative artifacts.

## Procedure

1. Verify source identity, item reference, date, and collection status.
2. For Web, extract dated context, events, seasonality, and public market signals.
3. For XHS, extract titles, user language, emotion, scenes, and comment concerns.
4. For Douyin, extract 0–5 second visual and spoken hooks, pacing, conflict, turn,
   audio, transcript structure, and CTA.
5. For history, identify reused structures, failures, and reusable assets.
6. State how to adapt each observation without copying claims or wording.

## Output Contract

Produce `product_creative.research_insight_pack.v1` with item-level source refs,
source-specific fields, confidence, adaptation rules, and `not_product_fact=true`.

## Tool Boundary

Read source snapshots, artifacts, and history. Collection adapters may be planned by
the workflow, but this Skill does not log in, use Cookie, or start a live scrape.

## Failure Conditions

Fail or degrade when sources are missing, undated for a time-sensitive task,
unreadable, unrelated, or lack a stable item reference.

## Quality Rubric

- Every insight cites one source item.
- Each platform contributes its distinctive signal.
- Observation, interpretation, and adaptation are separate.
- Copying and product-fact contamination are explicitly prevented.

## Positive Examples

A Douyin item yields its first visual action, first spoken line, beat change, conflict,
turn, and reusable hook rule—not merely “the video is popular.”

## Negative Examples

Do not convert a creator's health claim, sales claim, or product description into a
fact about the current product.

## Verification

Check source coverage, required source-specific fields, dates, references,
degradation notes, and `not_product_fact=true`.
