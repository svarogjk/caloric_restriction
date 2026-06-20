---
name: pptx
description: Presentation creation and editing for the GEO Survival Analysis app. Use when creating, modifying, or regenerating the 14-slide PowerPoint deck, editing individual slides, changing slide content or styling, or running the presentation script. Also use when the user says things like "update slide 5", "add a new slide", "change the title", "regenerate the deck", or "fix the presentation".
---

# GEO Survival Analysis — PowerPoint Skill

## Quick Generate

```bash
cd backend && uv run python ../scripts/create_presentation.py
```

Output: `presentations/app_presentation.pptx`

Screenshots must exist in `presentations/screenshots/` (or a dated subfolder like `260123/`):
- `starting_page.png`
- `volcano_plot.png`
- `kaplan_meier_curves.png` (or `km_curves.png`)

---

## When to Edit vs Re-generate

**Re-generate** (run the script) when:
- Changing content in multiple slides
- Adding or removing a slide
- Updating screenshots

**Edit a helper call** (modify `scripts/create_presentation.py`) when:
- Fixing wording in one slide's content
- Adjusting a color or accent on a specific slide
- Tweaking a stat value or bullet point

After any edit to the script, re-generate to apply changes.

---

## Script Architecture

`scripts/create_presentation.py` is organized in three layers:

```
Primitive helpers   →   Slide template functions   →   create_presentation()
_rect, _oval,           add_title_slide,               Orchestrates all 14
_tb, _para,             add_stat_cards_slide,          slides in order,
_title_block            add_two_col_slide, ...         saves the .pptx
```

Every slide template calls `_set_bg(slide)` first, then `_title_block(slide, title, accent)`, then composes shapes and text using the primitives.

---

## Slide → Helper Mapping

| Slide | Title | Helper |
|-------|-------|--------|
| 1 | Title | `add_title_slide` |
| 2 | The Global Cancer Crisis | `add_stat_cards_slide` |
| 3 | The Root Cause | `add_two_col_slide` |
| 4 | The Untapped GEO Goldmine | `add_stat_cards_slide` |
| 5 | Why GEO Is Inaccessible Today | `add_workflow_slide` |
| 6 | Existing Tools and Their Limits | `add_table_slide` |
| 7 | Six Gaps No Existing Tool Closes | `add_gap_cards_slide` |
| 8 | Introducing GEO Survival Analysis | `add_pipeline_slide` |
| 9 | Gene Mapping: Platform Babel Problem | `add_two_col_slide` |
| 10 | Speed-Lightning: 600 Cancer Genes | `add_stat_cards_slide` |
| 11 | Demo: Getting Started | `add_image_slide` |
| 12 | Demo: Gene Results & Volcano Plot | `add_image_slide` |
| 13 | Demo: Kaplan-Meier Survival Curves | `add_image_slide` |
| 14 | Why GEO Survival Analysis Wins | `add_table_slide` |

---

## Design Warnings

Adapted from Anthropic's pptx skill — these are the most common failure modes:

- **Never repeat the same layout more than twice in a row.** The 14 slides use 7 distinct templates deliberately — preserve that variety when adding slides.
- **Never center body text.** Left-align bullets in columns. Center only: stat values (38pt), pipeline step labels, and image captions.
- **TEAL is the primary accent, not BLUE.** Blue is secondary. Don't swap them.
- **CORAL means danger/problem.** Don't use it for neutral or positive content.
- **Decorative ovals (`_oval`) only appear on the title slide.** Don't add them to other slides.
- **Don't put a table slide right after another table slide.** Break it up with a two-col or stat-cards slide.
- **Image slides have no `_title_block` underline** — they use a thinner manual `_rect` line at a different position. Don't replace them with a standard `_title_block` call.

---

## Quality Assurance

After generating, **open the file visually** — python-pptx renders correctly but layout bugs (overlapping shapes, text clipping, wrong colors) are only visible in PowerPoint or LibreOffice.

Quick check from CLI using LibreOffice (if available):
```bash
libreoffice --headless --convert-to png presentations/app_presentation.pptx
```

The first render is almost never pixel-perfect on new slides. Check:
- Text is not clipped by the card boundary
- Accent colors match the slide's theme (teal for solution, coral for problem)
- Table rows have visible alternating fills
- Pipeline arrows are visible and properly spaced

---

## Adding a New Slide

1. Write a helper function following this pattern:
   ```python
   def add_my_slide(prs: Presentation, title: str, ...) -> None:
       slide = prs.slides.add_slide(prs.slide_layouts[6])
       _set_bg(slide)
       _title_block(slide, title, TEAL)  # choose accent color
       # compose shapes and text with _rect, _oval, _tb, _para
   ```
2. Call it in `create_presentation()` at the correct position.
3. Update the docstring at the top of `create_presentation.py` with the new slide number and title.

---

---

## Clinical Positioning Deck

**Title:** GEO Survival Analysis: Predictive Biomarkers & Advisory Treatment Guidance

**Audience:** Oncologists, clinical researchers, precision medicine leads

**Output:** `presentations/clinical_positioning.pptx`

**Script:** `scripts/create_clinical_presentation.py`

### Slide Structure

| # | Title | Template | Notes |
|---|-------|----------|-------|
| 1 | GEO Survival Analysis: Predictive Biomarkers & Advisory Treatment Guidance | `add_title_slide` | Subtitle: "Cross-cohort expression biomarkers for any cancer" |
| 2 | The Gap: TCGA-Locked Tools Leave Rare Cancers Behind | `add_stat_cards_slide` | Stats: 200K+ GEO studies, 3 major tools TCGA-only |
| 3 | Competitive Landscape | `add_table_slide` | Us vs KMplot / GEPIA2 / OncoKB / cBioPortal — highlight GEO breadth + cross-cohort |
| 4 | What "Predictive" Means Here — and What It Doesn't | `add_two_col_slide` | Left: what we do (treatment-effect-modifying biomarkers via expression×treatment interaction; advisory treatments to discuss from CIViC/DGIdb + cohort outcomes). Right: what we don't claim (validated companion diagnostic, prescription, de-novo drug-matching) — advisory, research use only. |
| 5 | Cross-Cohort Meta-Analysis: Why 8 Cohorts >> 1 | `add_workflow_slide` | Steps: search → download → Cox per dataset → rank by consistency → forest + I² |
| 6 | Demo: Natural Language Query → Results in 5 Min | `add_image_slide` | Screenshot: starting_page.png |
| 7 | Volcano Plot & Hazard Ratios | `add_image_slide` | Screenshot: volcano_plot.png |
| 8 | Kaplan-Meier Curves: Population-Level Evidence | `add_image_slide` | Screenshot: kaplan_meier_curves.png |
| 9 | Forest Plot: Reproducibility Across Institutions | `add_two_col_slide` | Left: forest plot reading guide. Right: I² / Cochran Q interpretation |
| 10 | Stratified Medicine: High / Intermediate / Low Risk | `add_stat_cards_slide` | F17 roadmap: continuous Cox risk score + C-index validation (Oncotype DX logic) |
| 11 | Where We Fit in the Clinical Workflow | `add_two_col_slide` | Left: complementary to companion-diagnostic tools (OncoKB, cBioPortal). Right: expression adds predictive biomarkers + advisory treatment guidance |
| 12 | Roadmap: Toward Clinical-Grade Decision Support | `add_pipeline_slide` | F16 multivariate HR → F16b predictive biomarkers → F17 signature → F18 nomogram → F20 Oncologist Mode → F24 treatment context |

### Framing Rules (enforced in script docstring and copy)

- **"Predictive" = treatment-effect-modifying biomarkers** (expression×treatment interaction) + **advisory** treatment guidance — never a validated companion diagnostic, prescription, or de-novo drug-matching claim
- Treatment suggestions are framed **"to consider/discuss"**, never directives
- Every competitive comparison: **"complementary to, not replacing"** OncoKB / cBioPortal
- Slide 4 and slide 10: carry **"Advisory / For Research Use Only"** disclaimer text
- Cite real GSE accession IDs in any dataset examples (e.g. GSE12345)
- Accent colors: TEAL for our advantages, CORAL for the problem/gap slides (2, 4)

---

## References

- `references/helpers.md` — full signatures and parameter docs for every function
- `references/design.md` — color palette, typography scale, and layout variety rules
