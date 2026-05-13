"""Generate a 17-slide PowerPoint presentation about the GEO Survival Analysis app.

Slide structure (PyData Yerevan edition):
  1.  Title
  2.  The Global Cancer Crisis
  3.  The Root Cause: Failing to Use the Data We Have
  4.  The Untapped GEO Goldmine
  5.  Why GEO Is Inaccessible Today
  6.  Existing Tools and Their Limits
  7.  Engineering Challenges We Had to Solve
  8.  System Architecture
  9.  Gene Mapping: Solving the Platform Babel Problem
  10. Statistical Engine: lifelines
  11. AI Chat: Why Not Just ChatGPT?
  12. AI Chat Architecture: How It Works
  13. Demo: Getting Started (screenshot)
  14. Demo: Gene Results & Volcano Plot (screenshot)
  15. Demo: Kaplan-Meier Survival Curves (screenshot)
  16. Deployment Pipeline
  17. What We Learned
"""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

# ── Color palette ──────────────────────────────────────────────────────────────
BG       = RGBColor(0x0F, 0x19, 0x23)  # slide background — very dark navy
CARD     = RGBColor(0x1A, 0x27, 0x36)  # card fill
CARD_ALT = RGBColor(0x15, 0x20, 0x30)  # alternate card fill (table odd rows)
WHITE    = RGBColor(0xF0, 0xF0, 0xF0)  # primary text
MUTED    = RGBColor(0xA0, 0xAE, 0xC0)  # secondary / label text
LIGHT    = RGBColor(0xC8, 0xD6, 0xE5)  # body bullet text
TEAL     = RGBColor(0x2D, 0xD4, 0xA8)  # primary accent
BLUE     = RGBColor(0x60, 0xA5, 0xFA)  # secondary accent
PURPLE   = RGBColor(0xA7, 0x8B, 0xFA)  # tertiary accent
AMBER    = RGBColor(0xFB, 0xBF, 0x24)  # amber highlight
CORAL    = RGBColor(0xF9, 0x70, 0x66)  # danger / problem accent

# ── Primitive helpers ──────────────────────────────────────────────────────────

def _set_bg(slide) -> None:
    """Set the dark background on every slide."""
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = BG


def _rect(slide, left, top, width, height, fill_color=CARD, name: str = "") -> object:
    """Add a filled rectangle with no border."""
    shape = slide.shapes.add_shape(1, Inches(left), Inches(top), Inches(width), Inches(height))
    if name:
        shape.name = name
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()
    return shape


def _oval(slide, left, top, width, height, fill_color=TEAL, name: str = "") -> object:
    """Add a filled oval with no border."""
    shape = slide.shapes.add_shape(9, Inches(left), Inches(top), Inches(width), Inches(height))
    if name:
        shape.name = name
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()
    return shape


def _tb(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    name: str = "",
) -> object:
    """Return a textbox; caller sets paragraphs."""
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    if name:
        txBox.name = name
    txBox.text_frame.word_wrap = True
    return txBox


def _para(
    tf,
    text: str,
    size: int,
    color: RGBColor,
    bold: bool = False,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    new: bool = False,
    space_after: int = 0,
) -> None:
    """Set or append a paragraph in a text frame."""
    p = tf.add_paragraph() if new else tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.alignment = align
    if space_after:
        p.space_after = Pt(space_after)


def _title_block(slide, title: str, accent: RGBColor = TEAL) -> None:
    """Standard slide title (28 pt white) + thin coloured underline."""
    tb = _tb(slide, 0.5, 0.30, 12.333, 0.75, "Title")
    _para(tb.text_frame, title, 28, WHITE, bold=True)
    line = _rect(slide, 0.5, 0.95, 12.333, 0.04, fill_color=accent, name="TitleLine")


# ── Slide 1: Title ─────────────────────────────────────────────────────────────

def add_title_slide(prs: Presentation, title: str, sub1: str, sub2: str) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide)

    # Decorative circles
    _oval(slide, 10.0, -0.5, 4.0, 4.0, TEAL,   "DecorCircle1")
    _oval(slide, -1.0,  5.0, 3.5, 3.5, BLUE,   "DecorCircle2")
    # Accent bar
    _rect(slide, 5.25, 2.40, 2.833, 0.06, TEAL, "AccentLine")

    tb = _tb(slide, 1.5, 2.60, 10.333, 1.1, "MainTitle")
    _para(tb.text_frame, title, 44, WHITE, bold=True, align=PP_ALIGN.CENTER)

    tb2 = _tb(slide, 2.0, 3.89, 9.333, 1.2, "Subtitle")
    _para(tb2.text_frame, sub1,  20, TEAL,  align=PP_ALIGN.CENTER)
    _para(tb2.text_frame, sub2,  16, MUTED, align=PP_ALIGN.CENTER, new=True)


# ── Slide 2 & 4 style: three stat cards ───────────────────────────────────────

def add_stat_cards_slide(
    prs: Presentation,
    title: str,
    cards: list[tuple[str, str, RGBColor, str]],  # (stat, label, color, desc)
    context_line: str = "",
    subtitle: str = "",
    accent: RGBColor = TEAL,
) -> None:
    """3-card stats slide (like slides 2 & 4)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide)
    _title_block(slide, title, accent)

    if subtitle:
        tb = _tb(slide, 0.5, 1.05, 12.333, 0.45)
        _para(tb.text_frame, subtitle, 16, MUTED)

    card_top = 1.65 if not subtitle else 1.75
    xs = [0.5, 4.778, 9.056]
    cw = 3.778

    for idx, (stat, label, color, desc) in enumerate(cards[:3]):
        x = xs[idx]
        _rect(slide, x, card_top, cw, 3.40, CARD, f"StatCard{idx}")
        # Accent bar on left edge
        _rect(slide, x, card_top, 0.08, 3.40, color, f"CardAccent{idx}")

        tb_stat = _tb(slide, x, card_top + 0.30, cw, 1.05)
        _para(tb_stat.text_frame, stat,  38, color, bold=True, align=PP_ALIGN.CENTER)

        tb_label = _tb(slide, x, card_top + 1.40, cw, 0.50)
        _para(tb_label.text_frame, label, 18, WHITE, bold=True, align=PP_ALIGN.CENTER)

        tb_desc = _tb(slide, x, card_top + 1.95, cw, 1.30)
        _para(tb_desc.text_frame, desc,  14, MUTED, align=PP_ALIGN.CENTER)

    if context_line:
        tb_ctx = _tb(slide, 0.5, 5.60, 12.333, 0.55)
        _para(tb_ctx.text_frame, context_line, 16, MUTED, align=PP_ALIGN.CENTER)


# ── Slide 3 style: two-column problem/opportunity ─────────────────────────────

def add_two_col_slide(
    prs: Presentation,
    title: str,
    left_header: str,
    left_header_color: RGBColor,
    left_bullets: list[str],
    right_header: str,
    right_bullets: list[str],
    accent: RGBColor = TEAL,
    bottom_badge: str = "",
) -> None:
    """Two-column problem/solution slide (like slide 3 and new slide 9)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide)
    _title_block(slide, title, accent)

    # Left column — no card, just text
    tb_lh = _tb(slide, 0.5, 1.20, 6.0, 0.50, "LeftHeader")
    _para(tb_lh.text_frame, left_header, 18, left_header_color, bold=True)

    tb_lb = _tb(slide, 0.5, 1.80, 6.0, 4.0, "LeftBullets")
    tf = tb_lb.text_frame
    for i, bullet in enumerate(left_bullets):
        _para(tf, f"• {bullet}", 16, LIGHT, new=(i > 0), space_after=8)

    # Right column — card
    _rect(slide, 7.0, 1.20, 6.0, 4.60, CARD, "RightCard")
    tb_rh = _tb(slide, 7.15, 1.30, 5.70, 0.50, "RightHeader")
    _para(tb_rh.text_frame, right_header, 16, accent, bold=True, align=PP_ALIGN.CENTER)

    tb_rb = _tb(slide, 7.15, 1.90, 5.70, 3.80, "RightBullets")
    tf2 = tb_rb.text_frame
    for i, bullet in enumerate(right_bullets):
        _para(tf2, f"• {bullet}", 15, LIGHT, new=(i > 0), space_after=8)

    if bottom_badge:
        tb_b = _tb(slide, 0.5, 6.05, 12.333, 0.60, "BottomBadge")
        _para(tb_b.text_frame, bottom_badge, 16, TEAL, bold=True, align=PP_ALIGN.CENTER)


# ── Slide 5 style: workflow steps ─────────────────────────────────────────────

def add_workflow_slide(
    prs: Presentation,
    title: str,
    steps: list[tuple[str, str]],  # (number, label)
    badge_line1: str = "",
    badge_line2: str = "",
) -> None:
    """6-step workflow grid (like slide 5)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide)
    _title_block(slide, title, CORAL)

    row_defs = [(0, 3), (3, 6)]  # first 3 steps, last 3
    row_tops = [1.25, 3.05]
    col_xs   = [0.5, 2.45, 4.40]
    sw, sh   = 1.70, 1.60

    for row_i, (start, end) in enumerate(row_defs):
        row_steps = steps[start:end]
        yt = row_tops[row_i]
        for col_i, (num, label) in enumerate(row_steps):
            x = col_xs[col_i]
            _rect(slide, x, yt, sw, sh, CARD, f"Step{start + col_i}")
            tb_n = _tb(slide, x, yt + 0.08, sw, 0.40)
            _para(tb_n.text_frame, num, 14, CORAL, bold=True, align=PP_ALIGN.CENTER)
            tb_l = _tb(slide, x, yt + 0.55, sw, 0.90)
            _para(tb_l.text_frame, label, 14, LIGHT, align=PP_ALIGN.CENTER)
            # Arrow between cols (not after last)
            if col_i < len(row_steps) - 1:
                ax = x + sw + 0.02
                ay = yt + sh / 2 - 0.04
                arr = _rect(slide, ax, ay, 0.21, 0.08, CORAL, f"Arrow{start+col_i}")
        # Down arrow between rows (left column)
        if row_i == 0:
            _rect(slide, 0.5 + sw / 2 - 0.04, 2.85, 0.08, 0.20, CORAL, "DownArrow")

    # Result badge
    if badge_line1:
        _rect(slide, 6.35, 1.25, 6.483, 2.80, CORAL, "ResultBadge")
        tb_b1 = _tb(slide, 6.35, 1.60, 6.483, 0.60)
        _para(tb_b1.text_frame, badge_line1, 16, WHITE, align=PP_ALIGN.CENTER)
        if badge_line2:
            tb_b2 = _tb(slide, 6.35, 2.30, 6.483, 0.90)
            _para(tb_b2.text_frame, badge_line2, 32, WHITE, bold=True, align=PP_ALIGN.CENTER)


# ── Slide 6 & 14 style: comparison table ──────────────────────────────────────

def add_table_slide(
    prs: Presentation,
    title: str,
    col_headers: list[str],
    rows: list[list[str]],
    col_widths: list[float] | None = None,
    accent: RGBColor = TEAL,
) -> None:
    """Table slide with coloured header row and alternating fills."""
    from pptx.util import Inches as I_

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide)
    _title_block(slide, title, accent)

    n_cols = len(col_headers)
    n_rows = len(rows) + 1  # include header

    if col_widths is None:
        col_widths = [12.333 / n_cols] * n_cols

    total_w = sum(col_widths)
    table_left = Inches(0.5)
    table_top  = Inches(1.20)
    table_w    = Inches(total_w)
    table_h    = Inches(5.60)

    tbl = slide.shapes.add_table(n_rows, n_cols, table_left, table_top, table_w, table_h).table

    # Column widths
    for ci, cw in enumerate(col_widths):
        tbl.columns[ci].width = Inches(cw)

    # Header row
    for ci, hdr in enumerate(col_headers):
        cell = tbl.cell(0, ci)
        cell.text = hdr
        cell.text_frame.paragraphs[0].font.size = Pt(15)
        cell.text_frame.paragraphs[0].font.bold = True
        cell.text_frame.paragraphs[0].font.color.rgb = BG
        fill = cell.fill
        fill.solid()
        fill.fore_color.rgb = accent

    # Data rows
    for ri, row in enumerate(rows):
        fill_color = CARD if ri % 2 == 0 else CARD_ALT
        for ci, text in enumerate(row):
            cell = tbl.cell(ri + 1, ci)
            cell.text = text
            tf = cell.text_frame
            tf.paragraphs[0].font.size = Pt(13)
            tf.paragraphs[0].font.color.rgb = WHITE if ci == 0 else LIGHT
            tf.paragraphs[0].font.bold = (ci == 0)
            cell.fill.solid()
            cell.fill.fore_color.rgb = fill_color


# ── Slide 7 style: gap cards (2×3 grid) ───────────────────────────────────────

def add_gap_cards_slide(
    prs: Presentation,
    title: str,
    cards: list[tuple[str, str, RGBColor]],  # (heading, desc, color)
    accent: RGBColor = CORAL,
) -> None:
    """2×3 grid of gap cards (like slide 7)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide)
    _title_block(slide, title, accent)

    xs   = [0.5, 4.70, 8.90]
    ys   = [1.10, 3.00]
    cw, ch = 3.90, 1.70

    for idx, (heading, desc, color) in enumerate(cards[:6]):
        col = idx % 3
        row = idx // 3
        x, y = xs[col], ys[row]
        _rect(slide, x, y, cw, ch, CARD, f"GapCard{idx}")
        tb_h = _tb(slide, x + 0.15, y + 0.10, cw - 0.30, 0.50)
        _para(tb_h.text_frame, heading, 18, color, bold=True)
        tb_d = _tb(slide, x + 0.15, y + 0.65, cw - 0.30, 0.90)
        _para(tb_d.text_frame, desc, 14, MUTED)


# ── Slide 8 style: pipeline steps ─────────────────────────────────────────────

def add_pipeline_slide(
    prs: Presentation,
    title: str,
    tagline: str,
    steps: list[tuple[str, str, str, RGBColor]],  # (step_label, heading, desc, color)
    bottom_text: str = "",
) -> None:
    """Horizontal pipeline (like slide 8)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide)
    _title_block(slide, title, TEAL)

    tb_tag = _tb(slide, 0.5, 0.95, 12.333, 0.45)
    _para(tb_tag.text_frame, tagline, 16, MUTED)

    n = len(steps)
    sw = 1.75
    gap = (12.333 - n * sw) / (n - 1) if n > 1 else 0
    st = 1.50
    sh = 3.60

    for i, (step_lbl, heading, desc, color) in enumerate(steps):
        x = 0.5 + i * (sw + gap)
        _rect(slide, x, st, sw, sh, CARD, f"PipeStep{i}")

        tb_sl = _tb(slide, x, st + 0.12, sw, 0.38)
        _para(tb_sl.text_frame, step_lbl, 14, MUTED, bold=True, align=PP_ALIGN.CENTER)

        tb_hd = _tb(slide, x, st + 0.55, sw, 0.55)
        _para(tb_hd.text_frame, heading, 16, color, bold=True, align=PP_ALIGN.CENTER)

        tb_dc = _tb(slide, x, st + 1.15, sw, 2.30)
        _para(tb_dc.text_frame, desc, 14, LIGHT, align=PP_ALIGN.CENTER)

        if i < n - 1:
            ax = x + sw + 0.02
            ay = st + sh / 2 - 0.04
            _rect(slide, ax, ay, gap - 0.04, 0.08, TEAL, f"PipeArrow{i}")

    if bottom_text:
        _rect(slide, 0.5, 5.25, 12.333, 0.65, TEAL, "BottomHighlight")
        tb_bt = _tb(slide, 0.5, 5.28, 12.333, 0.55)
        _para(tb_bt.text_frame, bottom_text, 18, BG, bold=True, align=PP_ALIGN.CENTER)


# ── Architecture diagram (layered boxes) ──────────────────────────────────────

def add_architecture_slide(
    prs: Presentation,
    title: str,
    layers: list[tuple[str, list[str], RGBColor]],  # (label, box_texts, color)
    accent: RGBColor = TEAL,
) -> None:
    """Vertical stack of labeled rows of boxes — system architecture diagram."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide)
    _title_block(slide, title, accent)

    n_layers  = len(layers)
    row_h     = 0.90
    arrow_h   = 0.15
    total     = n_layers * row_h + (n_layers - 1) * arrow_h
    start_y   = 1.0 + (6.50 - total) / 2  # vertically centred in available space

    label_x    = 0.30
    label_w    = 1.50
    box_area_x = 2.05
    box_area_w = 11.133
    gap        = 0.10

    for i, (label, boxes, color) in enumerate(layers):
        y  = start_y + i * (row_h + arrow_h)

        # Row label (right-aligned muted)
        tb_lbl = _tb(slide, label_x, y + 0.25, label_w, 0.40)
        _para(tb_lbl.text_frame, label, 11, MUTED, align=PP_ALIGN.RIGHT)

        # Equal-width boxes
        n  = len(boxes)
        bw = (box_area_w - (n - 1) * gap) / n
        for j, text in enumerate(boxes):
            bx = box_area_x + j * (bw + gap)
            _rect(slide, bx, y, bw, row_h, CARD, f"ArchBox{i}_{j}")
            _rect(slide, bx, y, bw, 0.07, color, f"ArchStripe{i}_{j}")  # colour stripe
            tb_b = _tb(slide, bx, y + 0.18, bw, row_h - 0.25)
            _para(tb_b.text_frame, text, 13, LIGHT, align=PP_ALIGN.CENTER)

        # Down-arrow connector between layers
        if i < n_layers - 1:
            ax = box_area_x + box_area_w / 2 - 0.06
            _rect(slide, ax, y + row_h, 0.12, arrow_h, accent, f"ArchArrow{i}")


# ── Demo screenshot slide ──────────────────────────────────────────────────────

def add_image_slide(
    prs: Presentation,
    title: str,
    image_path: Path,
    caption: str,
) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide)

    tb = _tb(slide, 0.5, 0.30, 12.333, 0.75, "Title")
    _para(tb.text_frame, title, 24, WHITE, bold=True)
    _rect(slide, 0.5, 1.05, 12.333, 0.04, TEAL, "TitleLine")

    slide.shapes.add_picture(str(image_path), Inches(1.0), Inches(1.20), width=Inches(11.333))

    tb_cap = _tb(slide, 0.5, 6.50, 12.333, 0.75, "Caption")
    _para(tb_cap.text_frame, caption, 14, TEAL, align=PP_ALIGN.CENTER)


# ── Screenshot finder ──────────────────────────────────────────────────────────

def _find_screenshot(screenshots_dir: Path, *names: str) -> Path:
    """Find a screenshot by name, searching dated subdirs newest-first then root."""
    subdirs = sorted(
        [d for d in screenshots_dir.iterdir() if d.is_dir()],
        reverse=True,
    )
    for name in names:
        for d in subdirs + [screenshots_dir]:
            p = d / name
            if p.exists():
                return p
    raise FileNotFoundError(f"Screenshot not found: {names} in {screenshots_dir}")


# ── Main builder ───────────────────────────────────────────────────────────────

def create_presentation(output_path: Path, screenshots_dir: Path) -> None:
    """Create the full 17-slide PyData Yerevan presentation."""
    prs = Presentation()
    prs.slide_width  = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # ── Slide 1: Title ─────────────────────────────────────────────────────────
    add_title_slide(
        prs,
        "GEO Survival Analysis",
        "Mining 200K+ Public Datasets for Cancer Biomarkers",
        "PyData Yerevan  ·  FastAPI · lifelines · pydantic-ai · React",
    )

    # ── Slide 2: The Global Cancer Crisis ─────────────────────────────────────
    add_stat_cards_slide(
        prs,
        "The Global Cancer Crisis",
        cards=[
            ("20M+",    "New Diagnoses",  CORAL, "New cancer diagnoses\nevery year worldwide"),
            ("97%",     "Drug Failure",   AMBER, "Of oncology drugs\nfail in clinical trials"),
            ("$1–2.6B", "Per Drug",       BLUE,  "Estimated cost to bring\none drug to market"),
        ],
        context_line="Cancer is the #2 cause of death worldwide  |  Median target-to-approval: 10–15 years",
    )

    # ── Slide 3: The Root Cause ────────────────────────────────────────────────
    add_two_col_slide(
        prs,
        "The Root Cause: Failing to Use the Data We Have",
        left_header="THE PROBLEM",
        left_header_color=CORAL,
        left_bullets=[
            "The problem is not a lack of data — it is a failure to extract insight from it",
            "Most drug targets are selected from single studies with small sample sizes",
            "Single-study findings rarely replicate — leading to expensive late-stage failures",
            "Billions of dollars invested, yet the 95% failure rate has not improved in decades",
        ],
        right_header="THE OPPORTUNITY",
        right_bullets=[
            "Better target selection from validated, multi-study evidence could halve failure rates",
            "200,000+ public datasets capturing gene expression vs. patient survival already exist",
            "The data to de-risk targets is there — we just need a way to systematically use it",
        ],
        accent=TEAL,
    )

    # ── Slide 4: The Untapped GEO Goldmine ────────────────────────────────────
    add_stat_cards_slide(
        prs,
        "The Untapped GEO Goldmine",
        subtitle="NCBI Gene Expression Omnibus — the world's largest public gene expression repository",
        cards=[
            ("200K+", "Datasets",        TEAL,   "Millions of patient samples\nacross every tumor type"),
            ("Live",  "Gene × Survival", BLUE,   "Expression vs. patient outcomes\n— exactly the signal needed"),
            ("Free",  "Growing Daily",   PURPLE, "Thousands of new datasets\nadded every year"),
        ],
    )

    # ── Slide 5: Why GEO Is Inaccessible Today ────────────────────────────────
    add_workflow_slide(
        prs,
        "Why GEO Is Inaccessible Today",
        steps=[
            ("1", "Search\nDatasets"),
            ("2", "Parse\nFormats"),
            ("3", "Map Probe\nto Gene"),
            ("4", "Find Survival\nMetadata"),
            ("5", "Run Cox +\nKaplan-Meier"),
            ("6", "Synthesize\nAcross Studies"),
        ],
        badge_line1="A skilled bioinformatician needs",
        badge_line2="2–6 Weeks",
    )

    # ── Slide 6: Existing Tools and Their Limits ──────────────────────────────
    add_table_slide(
        prs,
        "Existing Tools and Their Limits",
        col_headers=["Tool", "Key Limitation"],
        col_widths=[3.5, 8.833],
        rows=[
            ["KMplot.com",     "Static DB — ~6 cancer types, ~25K samples; no new GEO datasets"],
            ["GEPIA2",         "Fixed to TCGA + GTEx only; no GEO mining; no natural language"],
            ["cBioPortal",     "Curated TCGA/ICGC; no GEO mining; manual dataset selection"],
            ["R / Python DIY", "Unlimited scope — but requires 2–6 weeks of expert pipeline work"],
        ],
    )

    # ── Slide 7: Engineering Challenges ───────────────────────────────────────
    add_gap_cards_slide(
        prs,
        "Engineering Challenges We Had to Solve",
        cards=[
            ("Platform Babel",
             "100+ GPL platforms with proprietary probe IDs — no unified gene namespace",
             TEAL),
            ("Multi-GB Annotation Files",
             "GPL5175 = 4.3 GB SOFT files — stream only the platform table section (~14–36 MB)",
             AMBER),
            ("Metadata Heterogeneity",
             "Column names like 'os_time' or 'vital status: dead' — heterogeneous across 200K datasets",
             PURPLE),
            ("Async Parallel I/O",
             "10 datasets × 30–120 s each — sequential = 20 min; asyncio.gather = 2 min",
             TEAL),
            ("SSE Through Reverse Proxy",
             "Caddy/nginx buffer SSE by default — flush_interval=-1 is one line but must be known",
             BLUE),
            ("Memory Budget",
             "20K genes × 500 samples × float32 per dataset — filter to COSMIC 600 before analysis",
             CORAL),
        ],
        accent=TEAL,
    )

    # ── Slide 8: System Architecture ──────────────────────────────────────────
    add_architecture_slide(
        prs,
        "System Architecture",
        layers=[
            ("Client",
             ["React 18 + Redux Toolkit", "Recharts Visualization", "SSE Progress Stream"],
             BLUE),
            ("API",
             ["FastAPI Router", "JWT Auth", "SSE /search/stream"],
             TEAL),
            ("Orchestrator",
             ["GEOSurvivalWorkflowOrchestrator", "asyncio.gather", "LRU Cache (max 10)"],
             PURPLE),
            ("Services",
             ["GEOClient (NCBI Entrez)", "RankingService", "SurvivalAnalysisService", "GeneMappingService"],
             AMBER),
            ("Storage",
             ["SQLite / PostgreSQL (env swap)", "platform_mappings/*.parquet", "datasets/*.json"],
             MUTED),
        ],
        accent=TEAL,
    )

    # ── Slide 9: Gene Mapping — Solving the Platform Babel Problem ─────────────
    add_two_col_slide(
        prs,
        "Gene Mapping: Solving the Platform Babel Problem",
        left_header="THE CHALLENGE",
        left_header_color=CORAL,
        left_bullets=[
            "GEO hosts 100+ distinct microarray platforms (Affymetrix, Illumina, Agilent, and more)",
            "Each platform uses proprietary probe IDs — e.g. \"1007_s_at\" or \"ILMN_1343291\" — not gene names",
            "Without gene-level mapping, Cox regression on raw probes is biologically meaningless",
            "Manual curation of GPL annotation files: days of expert work per platform",
            "Inconsistent probe-to-gene: one probe may target multiple genes, one gene many probes",
        ],
        right_header="OUR AUTOMATED APPROACH",
        right_bullets=[
            "Auto-fetch GPL annotation file for every dataset at analysis time",
            "Parse probe_id → gene_symbol mapping in seconds — any platform, any study",
            "Aggregate multi-probe genes: mean expression per gene per sample",
            "Filter out non-expression platforms (methylation arrays, SNP chips, ChIP-seq)",
            "Disk cache: platform_mappings/*.parquet — survives restarts, never re-downloaded",
        ],
        accent=CORAL,
        bottom_badge="100+ platforms handled automatically  ·  Zero manual curation required",
    )

    # ── Slide 10: Statistical Engine ──────────────────────────────────────────
    add_two_col_slide(
        prs,
        "Statistical Engine: lifelines",
        left_header="METHODS",
        left_header_color=PURPLE,
        left_bullets=[
            "Median split — expression → high / low groups per dataset",
            "Log-rank test — non-parametric group comparison (p-value)",
            "Cox PH regression — hazard ratio + 95% confidence interval",
            "KaplanMeierFitter — time-to-event survival probability curves",
            "Cross-cohort ranking — genes sorted by n_significant_datasets, then avg p-value",
            "Heterogeneity — Cochran Q statistic + I² on forest plots",
        ],
        right_header="DATA FLOW",
        right_bullets=[
            "INPUT: GSE series_matrix.txt.gz",
            "→ probe_id × sample expression matrix  (pandas DataFrame)",
            "→ probe → gene symbol  (GPL annotation, parquet cache)",
            "→ high / low groups  (median split per dataset)",
            "→ Cox PH fit  →  HR, p-value, 95% CI",
            "→ KM fitter  →  survival probability curves",
            "OUTPUT: ranked gene list  (cross-dataset consistency)",
        ],
        accent=PURPLE,
        bottom_badge="Significance: p < 0.05  ·  min_occurrence: 2 datasets  ·  ~600 COSMIC cancer genes",
    )

    # ── Slide 11: AI Chat — Domain Score ──────────────────────────────────────
    add_two_col_slide(
        prs,
        "AI Chat: Why Not Just ChatGPT?",
        left_header="THE GROUNDING MANDATE",
        left_header_color=CORAL,
        left_bullets=[
            "General LLMs produce plausible text from training data — no real data access",
            "Cannot cite a real dataset or report a reproducible survival signal",
            "Our agent MUST call at least one tool per substantive question",
            "5 grounding tools — each call cites a real GSE accession  (see next slide)",
            "Every answer is grounded in a real GSE accession and live NCBI data",
        ],
        right_header="DOMAIN SCORE (0–100)",
        right_bullets=[
            "+20 per tool called  (max 40)",
            "+15 per GSE accession cited  (max 30)",
            "+15 for HR / p-value / n= samples in text",
            "+15 for user organism or candidate gene in text",
            "DS ≥ 70  →  green badge  (target: ≥ 60% of queries)",
            "DS 0–20  →  acceptable for conceptual questions only",
            "Logged: grep chat_metrics geo_logs/app.log",
        ],
        accent=TEAL,
        bottom_badge="Every response grounded in real GEO data — not training-set knowledge",
    )

    # ── Slide 12: AI Chat Architecture ────────────────────────────────────────
    add_architecture_slide(
        prs,
        "AI Chat Architecture: How It Works",
        layers=[
            ("User",
             ["React Chat UI", "Natural language question", "Streaming response (SSE)"],
             BLUE),
            ("Agent",
             ["pydantic-ai Agent", "Mistral (default)  ·  Claude Haiku (optional)",
              "Dynamic system prompt", "History trim  ≤16K chars"],
             TEAL),
            ("5 Tools",
             ["search_known_datasets", "search_geo_datasets",
              "get_gene_info", "estimate_query", "get_user_recent_results"],
             AMBER),
            ("Data",
             ["GEO dataset cache (parquet)", "NCBI Entrez live",
              "Mistral embed 1024-dim (RAG)", "SQLite results history"],
             PURPLE),
        ],
        accent=TEAL,
    )

    # ── Slide 13: Demo — Getting Started ──────────────────────────────────────
    add_image_slide(
        prs,
        "Demo: Getting Started",
        _find_screenshot(screenshots_dir, "starting_page.png"),
        'Type a natural language query — e.g. "What genes predict poor survival in triple-negative breast cancer?"',
    )

    # ── Slide 14: Demo — Gene Results & Volcano Plot ──────────────────────────
    add_image_slide(
        prs,
        "Demo: Gene Results & Volcano Plot",
        _find_screenshot(screenshots_dir, "volcano_plot.png"),
        "Ranked genes with hazard ratios, p-values, and risk direction consistency across datasets",
    )

    # ── Slide 15: Demo — Survival Curves ──────────────────────────────────────
    add_image_slide(
        prs,
        "Demo: Kaplan-Meier Survival Curves",
        _find_screenshot(screenshots_dir, "kaplan_meier_curves.png", "km_curves.png"),
        "Compare survival probability between high and low expression groups — interpretable by clinicians",
    )

    # ── Slide 16: Deployment Pipeline ─────────────────────────────────────────
    add_two_col_slide(
        prs,
        "Deployment Pipeline",
        left_header="MULTI-STAGE DOCKER BUILD",
        left_header_color=TEAL,
        left_bullets=[
            "Stage 1: node:22-alpine — npm ci + vite build  (React SPA → /dist)",
            "Stage 2: uv:python3.13 — uv sync --frozen --no-dev  (.venv)",
            "Stage 3: python:3.13-slim runtime — copy .venv + frontend/dist",
            "CMD: alembic upgrade head && uvicorn app.main:app --port 8000",
            "GitHub Actions: push → build → push ghcr.io → SSH deploy",
        ],
        right_header="HETZNER CX32 · CADDY · DOCKER COMPOSE",
        right_bullets=[
            "Caddy: automatic TLS + flush_interval=-1  (enables SSE streaming)",
            "SQLite default; DATABASE_URL env var → PostgreSQL, no code change",
            "Named volumes: app_data · platform_mappings · geo_logs  (survive redeploy)",
            "Why Caddy not nginx: zero-config TLS + native SSE, one-line Caddyfile",
            "Cost: ~$10/mo  (CX32 — 4 vCPU, 8 GB RAM, 80 GB NVMe)",
        ],
        accent=TEAL,
        bottom_badge="git push → live in ~3 min  ·  zero-downtime docker compose up -d",
    )

    # ── Slide 17: What We Learned ──────────────────────────────────────────────
    add_gap_cards_slide(
        prs,
        "What We Learned",
        cards=[
            ("asyncio.gather",
             "Parallel downloads cut wall time from 20 min → 2 min — the single biggest win",
             TEAL),
            ("Hybrid metadata detection",
             "Regex catches ~70% of survival columns; pydantic-ai structured output handles the rest",
             PURPLE),
            ("Disk-first caching",
             "Parquet in platform_mappings/ survives restarts; OrderedDict LRU is a fast layer on top",
             BLUE),
            ("uv in Docker",
             "uv sync --frozen: reproducible, layer-cached, no requirements.txt drift",
             AMBER),
            ("SSE proxy config",
             "Default Caddy/nginx buffers kill real-time streaming — flush_interval=-1 is one line",
             CORAL),
            ("SQLite scales further",
             "aiosqlite + SQLAlchemy async handles concurrent requests; PostgreSQL is one env-var away",
             TEAL),
        ],
        accent=TEAL,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output_path)
    print(f"Presentation saved to {output_path}")


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    screenshots_dir = project_root / "presentations" / "screenshots"
    output_path = project_root / "presentations" / "app_presentation.pptx"

    if not screenshots_dir.exists():
        print(f"Error: Screenshots directory not found: {screenshots_dir}")
        raise SystemExit(1)

    create_presentation(output_path, screenshots_dir)
