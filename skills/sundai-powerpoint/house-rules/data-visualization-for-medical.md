# House rules — `data-visualization-for-medical`

Rules here override the defaults in `skills/data-visualization-for-medical/SKILL.md`.
See [README.md](README.md) for how to write a good one.

## Seeded examples

- Use the corporate colour palette at `[path]`, and verify it against a
  colour-blindness simulator before use. Our previous palette failed for
  deuteranopia.
- Every Kaplan-Meier figure includes numbers at risk and censoring marks. No
  exceptions, including for slide versions.
- Never truncate a y-axis on an efficacy figure. On safety figures, state the
  truncation on the figure itself.

## YOUR RULES — ADD BELOW THIS LINE

- Quantitative multi-series slides (≥3 series or ≥3 categories) require an **editable** native OOXML PowerPoint chart with embedded Excel (python-pptx / pptxgenjs). SVG figures or a companion editable .xlsx are also allowed. Matplotlib/raster PNG embeds are last-resort fallback only when native charts cannot be created — and must be called out in speaker notes. Bullets alone are not enough; native editable charts are the primary path (not optional decoration).
