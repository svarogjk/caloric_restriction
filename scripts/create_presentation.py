"""Generate a 12-slide PowerPoint presentation about the GEO Survival Analysis app.

Slide structure:
  1.  Title
  2.  The Global Cancer Crisis
  3.  The Drug Discovery Problem
  4.  The Untapped GEO Goldmine
  5.  Why GEO Is Inaccessible Today
  6.  Existing Tools and Their Limits
  7.  Core Limitations Across All Tools
  8.  Introducing GEO Survival Analysis
  9.  Demo: Getting Started (screenshot)
  10. Demo: Gene Results & Volcano Plot (screenshot)
  11. Demo: Survival Curves (screenshot)
  12. Why We Win: Side-by-Side Comparison
"""

from pathlib import Path

from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


def _find_screenshot(screenshots_dir: Path, *names: str) -> Path:
    """Find a screenshot by name, searching dated subdirs newest-first then root."""
    subdirs = sorted(
        [d for d in screenshots_dir.iterdir() if d.is_dir()],
        reverse=True,
    )
    search_dirs = subdirs + [screenshots_dir]
    for name in names:
        for d in search_dirs:
            p = d / name
            if p.exists():
                return p
    raise FileNotFoundError(f"Screenshot not found: {names} in {screenshots_dir}")


def add_title_slide(prs: Presentation, title: str, subtitle: str) -> None:
    """Add a title slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(12.333), Inches(1.5))
    tf = txBox.text_frame
    tf.paragraphs[0].text = title
    tf.paragraphs[0].font.size = Pt(44)
    tf.paragraphs[0].font.bold = True
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER

    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(4.2), Inches(12.333), Inches(1))
    tf = txBox.text_frame
    tf.paragraphs[0].text = subtitle
    tf.paragraphs[0].font.size = Pt(24)
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER


def add_content_slide(prs: Presentation, title: str, bullets: list[str], font_size: int = 22) -> None:
    """Add a content slide with bullet points."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12.333), Inches(1))
    tf = txBox.text_frame
    tf.paragraphs[0].text = title
    tf.paragraphs[0].font.size = Pt(32)
    tf.paragraphs[0].font.bold = True

    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.5), Inches(5.2))
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"• {bullet}"
        p.font.size = Pt(font_size)
        p.space_after = Pt(10)


def add_two_column_slide(
    prs: Presentation,
    title: str,
    left_header: str,
    right_header: str,
    rows: list[tuple[str, str]],
) -> None:
    """Add a slide with two labelled columns (tool comparison table)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.9))
    tf = txBox.text_frame
    tf.paragraphs[0].text = title
    tf.paragraphs[0].font.size = Pt(30)
    tf.paragraphs[0].font.bold = True

    # Column headers
    for col, (x, w, text) in enumerate([
        (0.5, 4.5, left_header),
        (5.2, 7.5, right_header),
    ]):
        txBox = slide.shapes.add_textbox(Inches(x), Inches(1.35), Inches(w), Inches(0.45))
        tf = txBox.text_frame
        tf.paragraphs[0].text = text
        tf.paragraphs[0].font.size = Pt(16)
        tf.paragraphs[0].font.bold = True

    # Divider line
    from pptx.util import Emu
    from pptx.dml.color import RGBColor
    line = slide.shapes.add_connector(
        1,  # MSO_CONNECTOR.STRAIGHT
        Inches(0.5), Inches(1.85),
        Inches(12.833), Inches(1.85),
    )
    line.line.width = Emu(12700)  # 1 pt

    # Rows
    row_y_start = 1.95
    row_height = 0.52
    for i, (left_text, right_text) in enumerate(rows):
        y = row_y_start + i * row_height

        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(y), Inches(4.5), Inches(row_height))
        tf = txBox.text_frame
        tf.word_wrap = True
        tf.paragraphs[0].text = left_text
        tf.paragraphs[0].font.size = Pt(14)
        tf.paragraphs[0].font.bold = True

        txBox = slide.shapes.add_textbox(Inches(5.2), Inches(y), Inches(7.5), Inches(row_height))
        tf = txBox.text_frame
        tf.word_wrap = True
        tf.paragraphs[0].text = right_text
        tf.paragraphs[0].font.size = Pt(13)


def add_image_slide(
    prs: Presentation, title: str, image_path: Path, description: str
) -> None:
    """Add a slide with an image and description."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
    tf = txBox.text_frame
    tf.paragraphs[0].text = title
    tf.paragraphs[0].font.size = Pt(28)
    tf.paragraphs[0].font.bold = True

    slide.shapes.add_picture(str(image_path), Inches(1.5), Inches(1.2), width=Inches(10))

    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(6.5), Inches(12.333), Inches(0.8))
    tf = txBox.text_frame
    tf.paragraphs[0].text = description
    tf.paragraphs[0].font.size = Pt(14)
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER


def create_presentation(output_path: Path, screenshots_dir: Path) -> None:
    """Create the full 12-slide presentation."""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # ── Slide 1: Title ────────────────────────────────────────────────────────
    add_title_slide(
        prs,
        "GEO Survival Analysis",
        "AI-Powered Cancer Genomics — From Public Data to Drug Targets in Minutes",
    )

    # ── Slide 2: The Global Cancer Crisis ────────────────────────────────────
    add_content_slide(
        prs,
        "The Global Cancer Crisis",
        [
            "20 million new diagnoses and 10 million deaths every year",
            "Cancer is the #2 cause of death worldwide",
            ">95% of oncology drugs fail in clinical trials",
            "Average cost to bring one cancer drug to market: $2.6 billion",
            "Phase III failure rates exceed 50% — drugs fail at peak investment",
            "Median timeline from target to approval: 12–15 years",
        ],
    )

    # ── Slide 3: The Drug Discovery Problem ───────────────────────────────────
    add_content_slide(
        prs,
        "The Root Cause: Failing to Use the Data We Have",
        [
            "The problem is not a lack of data — it is a failure to extract insight",
            "Billions of dollars and decades of research produce a 95% failure rate",
            "Most drug targets are selected from single studies with small sample sizes",
            "Single-study findings rarely replicate — leading to expensive late-stage failures",
            "Better target selection from validated, multi-study evidence could halve failure rates",
        ],
    )

    # ── Slide 4: The Untapped GEO Goldmine ───────────────────────────────────
    add_content_slide(
        prs,
        "The Untapped GEO Goldmine",
        [
            "NCBI Gene Expression Omnibus: world's largest public gene expression repository",
            "200,000+ datasets — millions of patient samples across virtually every tumor type",
            "Captures gene expression vs. patient survival outcomes — exactly the signal needed",
            "Thousands of new datasets added every year as research is published",
            "This resource exists, is free, and is largely untapped by the field",
        ],
    )

    # ── Slide 5: Why GEO Is Inaccessible Today ───────────────────────────────
    add_content_slide(
        prs,
        "Why GEO Is Inaccessible Today",
        [
            "Searching and evaluating hundreds of datasets manually",
            "Downloading and parsing heterogeneous file formats (GPL, GSE, soft, matrix)",
            "Mapping probe IDs to gene symbols across dozens of microarray platforms",
            "Detecting survival metadata buried in inconsistently named columns",
            "Running Cox regression and Kaplan-Meier per gene, per dataset",
            "Synthesizing results across studies — a skilled bioinformatician needs 2–6 weeks",
        ],
    )

    # ── Slide 6: Existing Tools and Their Limits ─────────────────────────────
    add_two_column_slide(
        prs,
        "Existing Tools and Their Limits",
        "Tool",
        "Key Limitation",
        [
            ("KMplot.com", "Static DB — ~6 cancer types, ~25,000 samples; no new datasets"),
            ("GEPIA2 / GEPIA", "Fixed to TCGA + GTEx only (~10,000 samples); no GEO mining"),
            ("cBioPortal", "Fixed TCGA/ICGC pool; manual dataset selection; no GEO mining"),
            ("PrognoScan", "Unmaintained since ~2010; ~220 fixed datasets; no AI features"),
            ("SurvExpress", "Small curated set; no NL interface; requires bioinformatics expertise"),
            ("R / Python DIY", "Unlimited scope but requires programming and full manual pipeline"),
        ],
    )

    # ── Slide 7: Core Limitations Across All Tools ───────────────────────────
    add_content_slide(
        prs,
        "Six Gaps No Existing Tool Closes",
        [
            "Static databases — thousands of new GEO datasets deposited annually are ignored",
            "Narrow coverage — 5–15 common cancers; rare cancers entirely absent",
            "No intelligent quality assessment — researchers must manually inspect every dataset",
            "Single-dataset only — no automated cross-dataset meta-analysis for robust hits",
            "High technical barrier — R/Python tools inaccessible to most cancer biologists",
            "No iterative exploration — one-shot queries with no context, refinement, or AI guidance",
        ],
    )

    # ── Slide 8: Introducing GEO Survival Analysis ───────────────────────────
    add_content_slide(
        prs,
        "Introducing GEO Survival Analysis",
        [
            "End-to-end AI platform: natural language query → ranked, validated survival genes",
            "Queries the live NCBI GEO API — every dataset ever deposited is searchable",
            "LLM agent scores each dataset 0–10 for survival relevance before analysis begins",
            "Automatic probe-to-gene mapping, survival metadata detection, Cox + KM per gene",
            "Cross-dataset meta-analysis surfaces genes consistent across independent cohorts",
            "Full pipeline completes in under 5 minutes — no code, no manual configuration",
        ],
    )

    # ── Slide 9: Demo — Getting Started ──────────────────────────────────────
    add_image_slide(
        prs,
        "Demo: Getting Started",
        _find_screenshot(screenshots_dir, "starting_page.png"),
        'Type a natural language query — e.g. "What genes predict poor survival in triple-negative breast cancer?"',
    )

    # ── Slide 10: Demo — Gene Results & Volcano Plot ─────────────────────────
    add_image_slide(
        prs,
        "Demo: Gene Results & Volcano Plot",
        _find_screenshot(screenshots_dir, "volcano_plot.png"),
        "Ranked genes with hazard ratios, p-values, and risk direction consistency across datasets",
    )

    # ── Slide 11: Demo — Survival Curves ─────────────────────────────────────
    add_image_slide(
        prs,
        "Demo: Kaplan-Meier Survival Curves",
        _find_screenshot(screenshots_dir, "kaplan_meier_curves.png", "km_curves.png"),
        "Compare survival probability between high and low expression groups — interpretable by clinicians",
    )

    # ── Slide 12: Why We Win — Side-by-Side Comparison ───────────────────────
    add_two_column_slide(
        prs,
        "Why GEO Survival Analysis Wins",
        "Dimension",
        "GEO Survival Analysis vs. Existing Tools",
        [
            ("Dataset scope", "200,000+ live GEO datasets  vs.  200–10,000 pre-curated"),
            ("Cancer type coverage", "Any cancer type in GEO  vs.  5–15 common types only"),
            ("New dataset access", "Real-time via NCBI API  vs.  Not available"),
            ("Dataset quality filtering", "AI-powered relevance ranking  vs.  Manual or absent"),
            ("Survival metadata detection", "LLM-automated  vs.  Manual column inspection"),
            ("Cross-dataset meta-analysis", "Core feature  vs.  Not available in any tool"),
            ("Natural language interface", "Full conversational UI  vs.  Not available"),
            ("Time to first result", "Under 5 minutes  vs.  Days to weeks"),
        ],
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
        exit(1)

    create_presentation(output_path, screenshots_dir)
