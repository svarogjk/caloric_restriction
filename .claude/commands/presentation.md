---
description: Generate PowerPoint presentation from screenshots in presentations/screenshots/
user-invocable: true
---

# Create App Presentation

Generate a 12-slide PowerPoint about the GEO Survival Analysis app.

```bash
cd backend && uv run python ../scripts/create_presentation.py
```

**Output**: `presentations/app_presentation.pptx`

## Slide Structure

**Challenge & Market Positioning (slides 1–7)**

1. Title Slide — GEO Survival Analysis
2. The Global Cancer Crisis — 20M diagnoses, 10M deaths, 95% drug failure rate
3. The Root Cause — failing to extract insight from existing data
4. The Untapped GEO Goldmine — 200,000+ public datasets, mostly inaccessible
5. Why GEO Is Inaccessible Today — 6-step manual workflow, 2–6 weeks per analysis
6. Existing Tools and Their Limits — comparison table (KMplot, GEPIA2, cBioPortal, etc.)
7. Six Gaps No Existing Tool Closes — core limitations shared across all competitors

**The Solution & Demo (slides 8–12)**

8. Introducing GEO Survival Analysis — end-to-end AI pipeline overview
9. Demo: Getting Started — screenshot of the chat interface
10. Demo: Gene Results & Volcano Plot — screenshot of ranked genes
11. Demo: Kaplan-Meier Survival Curves — screenshot of survival curves
12. Why We Win — side-by-side comparison table vs. existing tools

Edit `scripts/create_presentation.py` to customize slides.

## Screenshots

Place screenshots in `presentations/screenshots/` or a dated subfolder (e.g. `260123/`).
Required files: `starting_page.png`, `volcano_plot.png`, `kaplan_meier_curves.png` (or `km_curves.png`).
The script searches dated subdirectories newest-first, then falls back to the root screenshots folder.
