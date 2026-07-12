---
name: product-copy-pack
description: Generate a structured Product Copy Brain asset pack from Product Wiki and Product State, including selling-point copy, ecommerce main-image description, image prompt, and short-video storyboard text.
version: 0.1.0
author: product_creative
---

# Product Copy Pack Skill

## Purpose

Generate the M0 text foundation for downstream content production.

This skill does not create final images or videos. It creates the structured copy and creative descriptions that later image/video providers will consume.

## Required Inputs

The caller must provide a context pack with:

- `product_state.json`
- `wiki/SCHEMA.md`
- `wiki/index.md`
- `wiki/product/Product.md`
- `wiki/product/selling-points.md`
- `wiki/channels/ecommerce.md`
- `wiki/channels/douyin.md`
- Recent feedback preferences, when available

Optional inputs:

- Referenced product images or image summaries
- Previous generated artifacts
- Relevant experiment summaries

## Output Contract

Return a JSON object with:

```json
{
  "variants": [
    {
      "variant": 1,
      "style": "理性清晰型",
      "product_one_liner": "",
      "core_selling_points": [],
      "ecommerce_main_image_copy": {
        "headline": "",
        "subheadline": "",
        "supporting_labels": [],
        "visual_direction": ""
      },
      "image_generation_prompt": "",
      "short_video_storyboard": [
        {
          "shot": 1,
          "duration": "0-3s",
          "description": "",
          "caption": ""
        }
      ],
      "generation_notes": {
        "basis": "",
        "preference": "",
        "requires_human_review": true
      }
    }
  ]
}
```

## Generation Rules

- Use Product Wiki and Product State as the grounding source.
- Keep claims within the provided product evidence.
- Prefer short, usable phrases over long paragraphs.
- Main-image copy should be concise enough for ecommerce layout.
- Image prompts should describe subject, composition, style, lighting, background, text treatment, and constraints.
- Short-video storyboard should include 4-6 shots with duration, scene description, and caption.
- Incorporate confirmed feedback preferences from Product State.
- If context is weak, mark uncertainty in `generation_notes.basis` instead of inventing product facts.

## Human Review Boundary

The generated copy pack is an artifact, not a Product Brain update.

This skill may suggest:

- Better selling-point phrasing
- Visual direction options
- Channel expression ideas
- Future update candidates

This skill must not directly modify:

- `wiki/product/Product.md`
- `wiki/product/positioning.md`
- `wiki/product/selling-points.md`
- `wiki/compliance/*`
- `structured/product_state.json`
- Any formal Skill prompt or Skill code

Product Brain changes must go through an evolution proposal and explicit user apply.

## Failure Handling

If the model cannot produce valid JSON:

- Preserve the raw model output as artifact metadata.
- Fall back to deterministic rule-based generation.
- Mark the artifact with `generation_method: fallback`.

If required context is missing:

- Generate a minimal draft using available Product State.
- Include missing-context notes in `generation_notes`.

