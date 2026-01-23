# Create App Presentation

Generate an 8-slide PowerPoint presentation about the GEO Survival Analysis app.

## Usage

Run this command to generate or regenerate the presentation using screenshots from `presentations/screenshots/`.

## Execution

```bash
cd backend && uv run python ../scripts/create_presentation.py
```

## Output

The presentation will be saved to: `presentations/app_presentation.pptx`

## Slide Structure

1. **Title Slide** - GEO Survival Analysis Tool
2. **Introduction** - What is GEO Survival Analysis?
3. **Getting Started** - Screenshot of starting page
4. **Gene Analysis Results** - Screenshot of gene results
5. **Volcano Plot** - Screenshot of volcano plot visualization
6. **Survival Curves** - Screenshot of Kaplan-Meier curves
7. **Key Features** - List of main features
8. **Get Started Today** - Conclusion and call to action

## Customization

Edit `scripts/create_presentation.py` to modify:
- Slide content and titles
- Image positioning
- Font sizes
- Add/remove slides
