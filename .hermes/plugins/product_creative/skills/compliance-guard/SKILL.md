---
name: compliance-guard
description: Use when creative, script, storyboard, copy, packaging, or character choices need semantic risk review in addition to deterministic product rules.
---

# Compliance Guard

Detect semantic and visual implications that literal term matching misses. This Skill
adds review evidence; it never replaces deterministic policy or professional legal,
medical, or regulatory judgment.

## When to Use

Use before production authorization, after a material revision, or when health,
safety, efficacy, pregnancy, sensitive use, packaging, or platform review risk exists.

## Inputs

Read Product Grounding, allowed and forbidden claims, Creative Decision, Story
Package, Production Bible, user constraints, and deterministic check results.

## Procedure

1. Preserve every deterministic failure as a hard failure.
2. Review direct claims, implied claims, character identity, scene implication,
   product role, dialogue, captions, packaging treatment, and omission risk.
3. Separate confirmed risk, plausible warning, and insufficient evidence.
4. Recommend the smallest content revision that removes the risk.
5. Never certify general health, medical, or legal compliance.

## Output Contract

Contribute structured checks to `product_creative.qa_report.v1`, including status,
detail, evidence location, risk class, and recommended revision.

## Tool Boundary

Read policy and professional artifacts. Do not edit the artifacts, call Providers,
search for substitute claims, or update Product Brain.

## Failure Conditions

Fail when a deterministic rule fails, a prohibited or unsupported claim appears,
packaging is altered, sensitive use is depicted, or the evidence is insufficient for
a required claim.

## Quality Rubric

- Hard and semantic risks are separated.
- Every finding points to exact content.
- Warnings do not masquerade as legal conclusions.
- Suggested revisions preserve the creative intent where possible.
- A model PASS never overrides a deterministic FAIL.

## Positive Examples

Flag “准妈妈也能放心用” as an implied absolute safety claim even when the exact
forbidden phrase “孕妇绝对安全” is absent.

## Negative Examples

Do not approve a health claim because it sounds common, appears on another platform,
or receives a high creative score.

## Verification

Confirm deterministic precedence, evidence location, risk class, revision advice,
and the absence of unsupported certification language.
