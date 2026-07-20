---
name: creative-review
description: Use when three creative candidates need an independent, evidence-based selection or preview decision before script and production planning.
---

# Creative Review

Judge candidate artifacts independently from their creator. Prefer an explainable
decision over a flattering review and never override deterministic safety rules.

## When to Use

Use after three candidates exist, when selecting a direction, preparing preview,
revising a user choice, or detecting repeated and unproducible ideas.

## Inputs

Read Product Grounding, Research Insight Pack, the three candidates, historical
similarity evidence, user constraints, and production capability metadata.

## Procedure

1. Verify all candidates are complete and materially different.
2. Score product fit, 0–5 second stop power, story completeness, freshness,
   channel fit, feasibility, packaging safety, compliance safety, and repetition.
3. Explain the winning candidate and why each other candidate loses.
4. Respect an explicit user selection unless it violates a hard boundary.
5. Mark preview-required tasks without continuing to script or production.

## Output Contract

Produce `product_creative.creative_decision.v1` covering exactly three candidates,
one selection, two rejection reasons, dimension scores, and allowed deviation.

## Tool Boundary

Read artifacts, history, materials, and capability metadata. Do not rewrite the
candidates, call Providers, or mutate Product Brain.

## Failure Conditions

Fail when candidate coverage is incomplete, evidence is missing, scores are
unexplained, a hard rule is violated, or all candidates exceed repetition limits.

## Quality Rubric

- Scores cite observable candidate content.
- Selection reason states trade-offs.
- Rejection reasons are candidate-specific.
- Safety gates dominate subjective preference.
- Preview behavior matches autonomy mode.

## Positive Examples

Select a lower-novelty direction when exact packaging and a short deadline make the
exploration route unsafe, and state that trade-off explicitly.

## Negative Examples

Do not select the most “creative sounding” title without evaluating hook, story,
production, packaging, compliance, and historical repetition.

## Verification

Confirm score coverage, selected and rejected ID coverage, hard-gate precedence,
user-choice handling, and preview state.
