# Helper Function Reference

All functions are in `scripts/create_presentation.py`.

---

## Primitive Helpers

### `_set_bg(slide) -> None`
Sets the dark navy background (`#0F1923`) on a slide.  
Call first in every slide template.

```python
_set_bg(slide)
```

---

### `_rect(slide, left, top, width, height, fill_color=CARD, name="") -> shape`
Adds a filled rectangle with no border. All dimensions in inches.

| Param | Type | Description |
|-------|------|-------------|
| `left`, `top` | float | Position from slide top-left corner |
| `width`, `height` | float | Size in inches |
| `fill_color` | RGBColor | Fill color (default: `CARD` = `#1A2736`) |
| `name` | str | Optional shape name for debugging |

Used for: card backgrounds, accent bars, arrows, table overlays, pipeline step backgrounds.

```python
_rect(slide, 0.5, 1.5, 3.778, 3.40, CARD, "StatCard0")
_rect(slide, 0.5, 1.5, 0.08, 3.40, TEAL, "CardAccent0")  # thin left edge
```

---

### `_oval(slide, left, top, width, height, fill_color=TEAL, name="") -> shape`
Adds a filled oval with no border. Same dimension units as `_rect`.

Used only in `add_title_slide` for decorative background circles.

```python
_oval(slide, 10.0, -0.5, 4.0, 4.0, TEAL, "DecorCircle1")
```

---

### `_tb(slide, left, top, width, height, name="") -> txBox`
Creates a text box with word wrap enabled. Returns the textbox object; caller uses `_para()` to add text.

```python
tb = _tb(slide, 0.5, 1.20, 6.0, 0.50, "LeftHeader")
_para(tb.text_frame, "THE PROBLEM", 18, CORAL, bold=True)
```

---

### `_para(tf, text, size, color, bold=False, align=PP_ALIGN.LEFT, new=False, space_after=0) -> None`
Sets or appends a paragraph in a text frame.

| Param | Type | Description |
|-------|------|-------------|
| `tf` | TextFrame | The `.text_frame` of a textbox |
| `text` | str | Paragraph text |
| `size` | int | Font size in points |
| `color` | RGBColor | Font color |
| `bold` | bool | Bold weight |
| `align` | PP_ALIGN | `LEFT`, `CENTER`, or `RIGHT` |
| `new` | bool | `False` = set first paragraph; `True` = `add_paragraph()` |
| `space_after` | int | Space after paragraph in points |

When building a list of bullets, set `new=True` for every item after the first:

```python
tf = tb.text_frame
for i, bullet in enumerate(bullets):
    _para(tf, f"• {bullet}", 16, LIGHT, new=(i > 0), space_after=8)
```

---

### `_title_block(slide, title, accent=TEAL) -> None`
Standard slide title: 28pt white bold text at `(0.5, 0.30)` plus a thin 4px underline in `accent` color at `y=0.95`.

```python
_title_block(slide, "Why GEO Is Inaccessible Today", CORAL)
```

**Note:** `add_image_slide` does NOT use `_title_block` — it draws its own title + line at different positions (24pt, line at y=1.05).

---

## Slide Template Functions

### `add_title_slide(prs, title, sub1, sub2) -> None`
Slide 1. Decorative teal and blue ovals, centered title (44pt), two subtitle lines.

| Param | Description |
|-------|-------------|
| `title` | Main title (44pt white bold, centered) |
| `sub1` | First subtitle line (20pt teal, centered) |
| `sub2` | Second subtitle line (16pt muted, centered) |

```python
add_title_slide(prs, "GEO Survival Analysis", "AI-Powered Cancer Genomics", "From Public Data to Drug Targets in Minutes")
```

---

### `add_stat_cards_slide(prs, title, cards, context_line="", subtitle="", accent=TEAL) -> None`
Slides 2, 4, 10. Three horizontally-arranged stat cards, each with a colored left-edge accent bar.

| Param | Type | Description |
|-------|------|-------------|
| `title` | str | Slide title |
| `cards` | list[tuple[str, str, RGBColor, str]] | Up to 3 cards: `(stat, label, color, desc)` |
| `context_line` | str | Optional footnote line at the bottom (16pt muted, centered) |
| `subtitle` | str | Optional subtitle below title (16pt muted) |
| `accent` | RGBColor | Title underline color |

Each card tuple: `stat` (38pt bold in `color`), `label` (18pt white bold), `desc` (14pt muted).

```python
add_stat_cards_slide(
    prs, "The Global Cancer Crisis",
    cards=[
        ("20M+",    "New Diagnoses", CORAL, "New cancer diagnoses\nevery year worldwide"),
        ("97%",     "Drug Failure",  AMBER, "Of oncology drugs\nfail in clinical trials"),
        ("$1–2.6B", "Per Drug",      BLUE,  "Estimated cost to bring\none drug to market"),
    ],
    context_line="Cancer is the #2 cause of death worldwide",
)
```

---

### `add_two_col_slide(prs, title, left_header, left_header_color, left_bullets, right_header, right_bullets, accent=TEAL, bottom_badge="") -> None`
Slides 3, 9. Left column: plain text bullets. Right column: dark card with header + bullets.

| Param | Type | Description |
|-------|------|-------------|
| `left_header` | str | Left column header (18pt bold in `left_header_color`) |
| `left_header_color` | RGBColor | Color for left header text (use CORAL for "problem") |
| `left_bullets` | list[str] | Bullet strings — `•` is added automatically |
| `right_header` | str | Right card header (16pt, centered in `accent` color) |
| `right_bullets` | list[str] | Right card bullet strings |
| `bottom_badge` | str | Optional full-width line at bottom (16pt teal bold, centered) |

```python
add_two_col_slide(
    prs, "Gene Mapping: Solving the Platform Babel Problem",
    left_header="THE CHALLENGE", left_header_color=CORAL,
    left_bullets=["100+ distinct microarray platforms", ...],
    right_header="OUR AUTOMATED APPROACH",
    right_bullets=["Auto-fetch GPL annotation", ...],
    accent=CORAL,
    bottom_badge="100+ platforms handled automatically  ·  Zero manual curation",
)
```

---

### `add_workflow_slide(prs, title, steps, badge_line1="", badge_line2="") -> None`
Slide 5. 6-step grid (2 rows × 3 columns) with horizontal arrows between columns and a vertical arrow between rows. Optional right-side result badge.

| Param | Type | Description |
|-------|------|-------------|
| `steps` | list[tuple[str, str]] | Up to 6 steps: `(number_label, step_label)` |
| `badge_line1` | str | First line of right-side badge (16pt white) |
| `badge_line2` | str | Second line of badge (32pt white bold) — the "big stat" |

Title underline is always CORAL. Arrows are CORAL.

```python
add_workflow_slide(
    prs, "Why GEO Is Inaccessible Today",
    steps=[("1", "Search\nDatasets"), ("2", "Parse\nFormats"), ...],
    badge_line1="A skilled bioinformatician needs",
    badge_line2="2–6 Weeks",
)
```

---

### `add_table_slide(prs, title, col_headers, rows, col_widths=None, accent=TEAL) -> None`
Slides 6, 14. Table with colored header row and alternating dark/darker row fills.

| Param | Type | Description |
|-------|------|-------------|
| `col_headers` | list[str] | Column header labels (bold, dark text on `accent` bg) |
| `rows` | list[list[str]] | Data rows; first cell in each row is white+bold, rest are LIGHT |
| `col_widths` | list[float] \| None | Column widths in inches; defaults to equal distribution across 12.333" |
| `accent` | RGBColor | Header row background color |

Total available width: 12.333". Specify `col_widths` to control column proportions.

```python
add_table_slide(
    prs, "Existing Tools and Their Limits",
    col_headers=["Tool", "Key Limitation"],
    col_widths=[3.5, 8.833],
    rows=[["KMplot.com", "Static DB — ~6 cancer types, ..."], ...],
)
```

---

### `add_gap_cards_slide(prs, title, cards, accent=CORAL) -> None`
Slide 7. 2×3 grid of gap cards (3 columns, 2 rows). Each card: heading + description.

| Param | Type | Description |
|-------|------|-------------|
| `cards` | list[tuple[str, str, RGBColor]] | Up to 6 cards: `(heading, desc, color)` |
| `accent` | RGBColor | Title underline color (default: CORAL) |

Card heading: 18pt bold in `color`. Description: 14pt muted.

```python
add_gap_cards_slide(
    prs, "Six Gaps No Existing Tool Closes",
    cards=[
        ("Static Databases", "Thousands of new GEO datasets deposited annually are ignored", CORAL),
        ("Narrow Coverage",  "Only 5–15 common cancers; rare cancers entirely absent",       AMBER),
        ...
    ],
)
```

---

### `add_pipeline_slide(prs, title, tagline, steps, bottom_text="") -> None`
Slide 8. Horizontal pipeline: N equally-spaced step cards with teal arrows between them. Optional full-width bottom highlight bar.

| Param | Type | Description |
|-------|------|-------------|
| `tagline` | str | Subtitle line under title (16pt muted) |
| `steps` | list[tuple[str, str, str, RGBColor]] | `(step_label, heading, desc, color)` |
| `bottom_text` | str | Optional bottom bar text (18pt BG-colored on TEAL background) |

Step layout: step label (14pt muted bold, centered), heading (16pt `color` bold, centered), desc (14pt LIGHT, centered).

```python
add_pipeline_slide(
    prs, "Introducing GEO Survival Analysis",
    tagline="End-to-end AI platform: natural language query → ranked, validated survival genes",
    steps=[
        ("STEP 1", "NL Query",   "Ask in plain\nEnglish",   TEAL),
        ("STEP 2", "Search GEO", "Live NCBI\nAPI query",    BLUE),
        ...
    ],
    bottom_text="No code  ·  No manual config  ·  Under 5 minutes",
)
```

---

### `add_image_slide(prs, title, image_path, caption) -> None`
Slides 11–13. Full-width screenshot with title and caption.

| Param | Type | Description |
|-------|------|-------------|
| `title` | str | Slide title (24pt white bold — smaller than other slides) |
| `image_path` | Path | Absolute path to PNG/JPG file |
| `caption` | str | Caption below image (14pt teal, centered) |

Image is placed at `x=1.0", y=1.20"` with `width=11.333"` (height auto-scaled).

```python
add_image_slide(
    prs, "Demo: Getting Started",
    _find_screenshot(screenshots_dir, "starting_page.png"),
    'Type a natural language query — e.g. "lung adenocarcinoma survival"',
)
```

---

## Utility Functions

### `_find_screenshot(screenshots_dir, *names) -> Path`
Finds a screenshot file, searching dated subdirectories newest-first, then the root screenshots folder.

```python
_find_screenshot(screenshots_dir, "kaplan_meier_curves.png", "km_curves.png")
# tries dated subdirs first (e.g. 260123/), then root, accepting either filename
```

Raises `FileNotFoundError` if none of the names are found anywhere.

---

### `create_presentation(output_path, screenshots_dir) -> None`
Main orchestrator. Creates a `Presentation` with custom dimensions (13.333" × 7.5"), calls all 14 slide helpers in order, saves to `output_path`.

```python
create_presentation(
    Path("presentations/app_presentation.pptx"),
    Path("presentations/screenshots"),
)
```
