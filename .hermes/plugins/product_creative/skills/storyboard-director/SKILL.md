---
name: storyboard-director
description: Use when an approved Story Package must become a provider-independent, shot-level Production Bible with continuity, material, packaging, audio, and subtitle rules.
---

# Storyboard Director

Compile story intent into executable shots while preserving user timing, material,
packaging, and continuity constraints. Keep the result independent of any vendor API.

## When to Use

Use after an approved Story Package and before Provider payload compilation,
generation authorization, media production, or review.

## Inputs

Read the Creative Task Brief, Story Package, selected candidate, Product Grounding,
selected materials, packaging requirement, and provider capability metadata.

## Procedure

1. Allocate duration to hook, incident, escalation, turn, and ending.
2. Define each shot's composition, action, scene, characters, material inputs,
   caption, and narrative function.
3. Honor an explicit product reveal time at a real shot boundary.
4. Assign immutable product plates, generated backgrounds, characters, audio, and
   deterministic subtitles distinct roles.
5. Define continuity, retry, fallback, and delivery requirements.

## Output Contract

Produce `product_creative.production_bible.v1`. It must contain at least two
executable shots, asset roles, packaging strategy, continuity rules, provider
mapping, retry policy, and delivery requirements.

## Tool Boundary

Read artifacts, materials, and provider capability metadata. Do not call a Provider,
render media, alter source assets, or invent product packaging.

## Failure Conditions

Fail when total duration cannot be allocated, required material is missing, packaging
strategy conflicts with the brief, product reveal timing is impossible, or shots lack
narrative functions.

## Quality Rubric

- Every shot changes story state.
- Timing sums to the requested duration.
- Product and packaging roles are explicit.
- Continuity rules are checkable.
- Subtitles and mutable scene generation are separated from immutable packaging.

## Positive Examples

For “product appears around second 4,” end the pre-product shot at second 4 and place
the immutable product plate in the next shot.

## Negative Examples

Do not pass the full product image to a generative video model and promise that
Chinese packaging text will remain exact.

## Verification

Check duration sum, product reveal boundary, material IDs, packaging route,
continuity, subtitle strategy, retry limits, and narrative function coverage.
