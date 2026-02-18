---
description: Generate PowerPoint presentation from screenshots in presentations/screenshots/
user-invocable: true
---

# Create App Presentation

Generate an 8-slide PowerPoint about the GEO Survival Analysis app.

```bash
cd backend && uv run python ../scripts/create_presentation.py
```

**Output**: `presentations/app_presentation.pptx`

## Slide Structure

1. Title Slide - GEO Survival Analysis Tool
2. Introduction - What is GEO Survival Analysis?
3. Getting Started - Screenshot of starting page
4. Gene Analysis Results - Screenshot of gene results
5. Volcano Plot - Screenshot of volcano plot visualization
6. Survival Curves - Screenshot of Kaplan-Meier curves
7. Key Features - List of main features
8. Get Started Today - Conclusion

Edit `scripts/create_presentation.py` to customize slides.
