---
description: Generate PowerPoint presentation from screenshots in presentations/screenshots/
user-invocable: true
---

# Create App Presentation

Generate a 14-slide PowerPoint about the GEO Survival Analysis app.

```bash
cd backend && uv run python ../scripts/create_presentation.py
```

**Output**: `presentations/app_presentation.pptx`

## Style

Dark-theme design matching `presentations/260221_survival_analysis_presentation.pptx`:

| Element        | Value          |
|----------------|----------------|
| Background     | `#0F1923` (very dark navy) |
| Primary text   | `#F0F0F0` |
| Teal accent    | `#2DD4A8` (primary) |
| Blue accent    | `#60A5FA` |
| Purple accent  | `#A78BFA` |
| Amber          | `#FBBF24` |
| Coral          | `#F97066` (problem/danger) |
| Card fill      | `#1A2736` |
| Muted text     | `#A0AEC0` |

## Slide Structure

**Challenge & Market Positioning (slides 1–7)**

1. **Title Slide** — GEO Survival Analysis
2. **The Global Cancer Crisis** — 3 stat cards: 20M+ diagnoses, 97% drug failure, $1–2.6B cost
3. **The Root Cause** — two-column problem/opportunity layout
4. **The Untapped GEO Goldmine** — 3 stat cards: 200K+ datasets, live gene×survival signal, free & growing
5. **Why GEO Is Inaccessible Today** — 6-step workflow with 2–6 week cost badge
6. **Existing Tools and Their Limits** — comparison table (KMplot, GEPIA2, cBioPortal, etc.)
7. **Six Gaps No Existing Tool Closes** — 2×3 grid of gap cards

**The Solution & Technical Differentiators (slides 8–10)**

8. **Introducing GEO Survival Analysis** — 6-step pipeline: NL Query → Search → AI Score → Analyse → Meta → Results
9. **Gene Mapping: Solving the Platform Babel Problem** — two-column: challenge (100+ GPL platforms, probe IDs) vs. automated solution (fetch annotation, map probe→gene, filter non-expression platforms)
10. **Speed-Lightning: Focus on 600 Cancer Genes** — 3 stat cards: 20K+ full genome (hours), 600 cancer genes (curated), 30× speedup; sources: Cancer Gene Census, drug targets, biomarkers

**Demo (slides 11–13)**

11. **Demo: Getting Started** — screenshot of the chat interface
12. **Demo: Gene Results & Volcano Plot** — screenshot of ranked genes
13. **Demo: Kaplan-Meier Survival Curves** — screenshot of survival curves

**Win (slide 14)**

14. **Why GEO Survival Analysis Wins** — 10-row comparison table including gene mapping and 600-gene speed rows

## Screenshots

Place screenshots in `presentations/screenshots/` or a dated subfolder (e.g. `260123/`).
Required files: `starting_page.png`, `volcano_plot.png`, `kaplan_meier_curves.png` (or `km_curves.png`).
The script searches dated subdirectories newest-first, then falls back to the root screenshots folder.

## Editing Slides

Edit `scripts/create_presentation.py`. Key helpers:

| Function                  | Used for slides       |
|---------------------------|-----------------------|
| `add_title_slide`         | 1                     |
| `add_stat_cards_slide`    | 2, 4, 10              |
| `add_two_col_slide`       | 3, 9                  |
| `add_workflow_slide`      | 5                     |
| `add_table_slide`         | 6, 14                 |
| `add_gap_cards_slide`     | 7                     |
| `add_pipeline_slide`      | 8                     |
| `add_image_slide`         | 11, 12, 13            |
