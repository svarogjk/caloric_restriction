"""Generate an 8-slide PowerPoint presentation about the GEO Survival Analysis app."""

from pathlib import Path

from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


def add_title_slide(prs: Presentation, title: str, subtitle: str) -> None:
    """Add a title slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(12.333), Inches(1.5))
    tf = txBox.text_frame
    tf.paragraphs[0].text = title
    tf.paragraphs[0].font.size = Pt(44)
    tf.paragraphs[0].font.bold = True
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Subtitle
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(4.2), Inches(12.333), Inches(1))
    tf = txBox.text_frame
    tf.paragraphs[0].text = subtitle
    tf.paragraphs[0].font.size = Pt(24)
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER


def add_content_slide(prs: Presentation, title: str, bullets: list[str]) -> None:
    """Add a content slide with bullet points."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12.333), Inches(1))
    tf = txBox.text_frame
    tf.paragraphs[0].text = title
    tf.paragraphs[0].font.size = Pt(32)
    tf.paragraphs[0].font.bold = True

    # Bullets
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.5), Inches(5))
    tf = txBox.text_frame

    for i, bullet in enumerate(bullets):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = f"• {bullet}"
        p.font.size = Pt(22)
        p.space_after = Pt(12)


def add_image_slide(
    prs: Presentation, title: str, image_path: Path, description: str
) -> None:
    """Add a slide with an image and description."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
    tf = txBox.text_frame
    tf.paragraphs[0].text = title
    tf.paragraphs[0].font.size = Pt(28)
    tf.paragraphs[0].font.bold = True

    # Image (centered, scaled to fit)
    slide.shapes.add_picture(str(image_path), Inches(1.5), Inches(1.2), width=Inches(10))

    # Description
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(6.5), Inches(12.333), Inches(0.8))
    tf = txBox.text_frame
    tf.paragraphs[0].text = description
    tf.paragraphs[0].font.size = Pt(14)
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER


def create_presentation(output_path: Path, screenshots_dir: Path) -> None:
    """Create the full 8-slide presentation."""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Slide 1: Title
    add_title_slide(
        prs,
        "GEO Survival Analysis Tool",
        "Gene Expression & Survival Analysis Platform",
    )

    # Slide 2: Introduction
    add_content_slide(
        prs,
        "What is GEO Survival Analysis?",
        [
            "Analyzes gene expression data from GEO (Gene Expression Omnibus)",
            "Performs survival analysis to identify prognostic genes",
            "Uses Kaplan-Meier curves and Cox proportional hazards regression",
            "Aggregates results across multiple datasets for robust findings",
        ],
    )

    # Slide 3: Starting Page
    add_image_slide(
        prs,
        "Getting Started",
        _find_screenshot(screenshots_dir, "starting_page.png"),
        "Enter a natural language query to search for relevant GEO datasets",
    )

    # Slide 4: Gene Results
    add_image_slide(
        prs,
        "Gene Analysis Results",
        _find_screenshot(screenshots_dir, "gene_screenshot.png"),
        "View ranked genes with hazard ratios, p-values, and confidence intervals",
    )

    # Slide 5: Volcano Plot
    add_image_slide(
        prs,
        "Volcano Plot Visualization",
        _find_screenshot(screenshots_dir, "volcano_plot.png"),
        "Visualize gene significance: X-axis shows log2 hazard ratio, Y-axis shows -log10 p-value",
    )

    # Slide 6: Kaplan-Meier Curves
    add_image_slide(
        prs,
        "Survival Curves",
        _find_screenshot(screenshots_dir, "km_curves.png", "kaplan_meier_curves.png"),
        "Compare survival probability between high and low expression groups over time",
    )

    # Slide 7: Key Features
    add_content_slide(
        prs,
        "Key Features",
        [
            "Natural language search powered by LLM ranking",
            "Automatic survival analysis across multiple datasets",
            "Interactive volcano plots and Kaplan-Meier curves",
            "Gene ranking by statistical significance and effect size",
            "Export results for further analysis",
        ],
    )

    # Slide 8: Conclusion
    add_content_slide(
        prs,
        "Get Started Today",
        [
            "Search for any disease or condition with survival data",
            "Discover prognostic genes in minutes, not hours",
            "Built with FastAPI, React, and lifelines",
            "Open source and extensible",
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
