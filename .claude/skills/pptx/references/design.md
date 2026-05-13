# Design Reference

---

## Color Palette

All colors are defined as module-level constants in `scripts/create_presentation.py`.

| Constant | Hex | Use |
|----------|-----|-----|
| `BG` | `#0F1923` | Slide background — very dark navy |
| `CARD` | `#1A2736` | Card and table row fill (even rows) |
| `CARD_ALT` | `#152030` | Alternate table row fill (odd rows) |
| `WHITE` | `#F0F0F0` | Primary text, titles, card labels |
| `MUTED` | `#A0AEC0` | Secondary text, descriptions, taglines |
| `LIGHT` | `#C8D6E5` | Body bullet text inside cards |
| `TEAL` | `#2DD4A8` | Primary accent — solution, opportunity, pipeline arrows |
| `BLUE` | `#60A5FA` | Secondary accent — data/stats, neutral differentiators |
| `PURPLE` | `#A78BFA` | Tertiary accent — AI/ML features, unique capabilities |
| `AMBER` | `#FBBF24` | Warning / notable stat (e.g. "97% failure rate") |
| `CORAL` | `#F97066` | Danger / problem / challenge — use only for negative framing |

**Semantic rules:**
- TEAL = our solution, good outcomes, primary differentiators
- CORAL = the problem, the barrier, the gap — never use for positive content
- AMBER = striking statistics that need attention but aren't purely negative
- BLUE / PURPLE = neutral data points, secondary features
- MUTED / LIGHT = supporting text that should recede visually

---

## Typography Scale

| Element | Size | Color | Bold | Align |
|---------|------|-------|------|-------|
| Slide title | 28pt | WHITE | Yes | Left |
| Image slide title | 24pt | WHITE | Yes | Left |
| Title slide main | 44pt | WHITE | Yes | Center |
| Stat card value | 38pt | accent | Yes | Center |
| Stat card label | 18pt | WHITE | Yes | Center |
| Left column header | 18pt | accent | Yes | Left |
| Right card header | 16pt | accent | Yes | Center |
| Taglines / subtitles | 16pt | MUTED | No | Left |
| Body bullets | 16pt | LIGHT | No | Left |
| Pipeline step label | 14pt | MUTED | Yes | Center |
| Pipeline heading | 16pt | accent | Yes | Center |
| Pipeline desc | 14pt | LIGHT | No | Center |
| Gap card heading | 18pt | accent | Yes | Left |
| Gap card desc | 14pt | MUTED | No | Left |
| Table header | 15pt | BG | Yes | (default) |
| Table row col 0 | 13pt | WHITE | Yes | (default) |
| Table row col 1+ | 13pt | LIGHT | No | (default) |
| Context / footnote | 16pt | MUTED | No | Center |
| Image caption | 14pt | TEAL | No | Center |
| Bottom badge text | 16pt | TEAL | Yes | Center |
| Bottom highlight bar | 18pt | BG | Yes | Center |

---

## Layout Variety

The 14 slides use 7 distinct templates. When adding new slides, maintain variety:

| Template | Visual character | Good for |
|----------|-----------------|----------|
| `add_title_slide` | Large centered text + decorative ovals | Opening only |
| `add_stat_cards_slide` | Three equal cards with large numbers | Key metrics, quantified claims |
| `add_two_col_slide` | Left bullets + right dark card | Problem/solution, challenge/approach |
| `add_workflow_slide` | 2×3 numbered grid with arrows | Sequential steps, manual processes |
| `add_table_slide` | Full-width comparison table | Feature comparisons, tool benchmarks |
| `add_gap_cards_slide` | 2×3 grid of labeled cards | Multiple distinct gaps or features |
| `add_pipeline_slide` | Horizontal pipeline with arrows | End-to-end flows, architectures |
| `add_image_slide` | Full-width screenshot + caption | Demo / evidence |

**Never place the same layout on three consecutive slides.** The current 14-slide order deliberately alternates:
- Slides 2, 4 are both `stat_cards` — slide 3 (two-col) breaks them up
- Slides 6, 14 are both `table` — 7 other layouts separate them

---

## Design Warnings

These are the most common mistakes when editing or adding slides:

1. **Centering body text** — only center stat values, pipeline labels, and captions. Body bullets and left-column text must be left-aligned.

2. **Using CORAL for neutral content** — CORAL signals danger/problem to the audience. Using it for a neutral fact or positive claim breaks the visual language established across slides 3, 5, 7, and 9.

3. **Applying BLUE as primary accent** — BLUE is secondary. Slides that introduce our solution (1, 8) use TEAL. Reserve BLUE for data/stats that are neutral or third-party.

4. **Adding decorative ovals outside the title slide** — the `_oval` helper is used only in `add_title_slide` for the two background circles. Other slides use rectangles only.

5. **Reusing `add_table_slide` twice in a row** — tables are dense; two in a row exhausts the audience. Break them up with stat cards or a two-col slide.

6. **Forgetting `_set_bg`** — every slide template must call `_set_bg(slide)` as its first action or the background will default to white.

7. **Skipping visual verification** — always open the generated `.pptx` file. Text clipping, shape overlap, and color errors are invisible until rendered.

---

## Slide Dimensions

Custom widescreen: **13.333" × 7.5"** (16:9, set in `create_presentation()`).

Standard margins: `left=0.5"`, `right edge=12.833"` (= `left + 12.333"` content width).
Title block: `y=0.30"` (text), `y=0.95"` (underline). Content starts at `y≈1.20"`.
Safe bottom: keep content above `y=6.80"` to avoid clipping in most viewers.
