---
description: Generate PowerPoint presentation from screenshots in presentations/screenshots/
user-invocable: true
---

# Create App Presentation

Generate a 51-slide PowerPoint about the GEO Survival Analysis app.

```bash
cd backend && uv run python ../scripts/create_presentation.py
```

**Output**: `presentations/app_presentation.pptx`

## Preview Specific Slides

To check a change on just a few slides without regenerating (and reopening) the full deck:

```bash
cd backend && uv run python ../scripts/create_presentation.py --slides 5,12,20-22
```

Accepts comma-separated numbers and ranges (`5,12,20-22`). Writes only the requested
slides, in that order, to a separate `presentations/app_presentation.preview.pptx` —
the main deck is never touched, so this is safe to run even while
`app_presentation.pptx` is open in PowerPoint.

**Skill**: For detailed helper function reference and design guidance, use the `pptx` skill — it is auto-loaded when editing slides.

## Style

Light-theme design (conference/projector friendly), slate-neutral background with darkened accent hues for AA-level text contrast:

| Element        | Value          |
|----------------|----------------|
| Background     | `#F8FAFC` (slate-50) |
| Card fill      | `#F1F5F9` (slate-100) |
| Card alt / gridlines | `#E2E8F0` (slate-200) |
| Primary text (`INK`) | `#0F172A` (slate-900) |
| Body text (`LIGHT`)  | `#334155` (slate-700) |
| Muted text     | `#64748B` (slate-500) |
| Teal accent    | `#0F766E` (primary) |
| Blue accent    | `#1D4ED8` |
| Purple accent  | `#6D28D9` |
| Amber          | `#B45309` |
| Coral          | `#B91C1C` (problem/danger) |
| Teal pastel bg (`TEAL_DIM`)  | `#CCFBF1` |
| Coral pastel bg (`CORAL_DIM`) | `#FEE2E2` |
| Teal badge bg (`TEAL_DARK`) | `#99F6E4` |

All accent colors were chosen to keep ≥4.5:1 contrast against the white/slate-50 background when used as text — since the script reuses the same named constant for both fill and text roles throughout, flipping just this palette re-themes all 51 slides consistently.

## Slide Structure

**Hook & Problem (slides 1–2)**

1. **Title Slide** — GEO Survival Analysis
2. **The Problem: 200K+ Datasets Nobody Can Use** — combined intro/problem slide

**Domain Primer (slides 3–6)**

3. **What Is Survival Analysis?**
4. **Kaplan-Meier Curves: Visualising Survival Over Time**
5. **Hazard Ratio: One Number to Rule Them All**
6. **Meta-Analysis: Why N Datasets > 1 Dataset**

**What We Built (slide 7)**

7. **What We Built: NL Query → Results in 5 Minutes** — comparison table vs. KMplot, GEPIA2, OncoLnc, cBioPortal etc.

**Clinical Reality — predictive value + responsible use (slides 8–10)**

8. **Predictive Biomarkers: Benefit for Real Patients** — two-column: prognostic→predictive vs. patient benefit
9. **What 'Predictive' Means Here — and What It Doesn't** — two-column: honest claims vs. what's never claimed
10. **Limitations in Real Clinical Practice** — 2×3 grid of gap cards (HIPAA/PHI, RUO, underpowered interactions, etc.)

**Backend Deep Dive (slides 11–19)**

11. **Backend Architecture** — visual routes → services schema
12. **FastAPI: 4 Problems Solved for This App**
13. **Pydantic: One Model, Four Jobs**
14. **asyncio: Production Patterns Beyond gather()**
15. **pydantic-ai: Production-Grade AI Agents**
16. **lifelines: Survival Analysis in Python**
17. **SQLAlchemy Async: One Codebase, Two Databases**
18. **Mistral Embeddings: One SDK for Chat + RAG**
19. **uv: The Docker Layer Cache Insight**

**Frontend Deep Dive (slides 20–24)**

20. **Frontend Architecture** — visual component tree + Redux + API
21. **React 18: Component-Based UI Framework**
22. **Redux Toolkit: Predictable Global State**
23. **SSE: It Is Just HTTP — No Special Protocol Needed**
24. **Recharts: Declarative Data Visualisation for React**

**Pipeline & Services (slides 25–33)**

25. **The 6-Step Analysis Pipeline We Automate** — Search → Parse → Map → Find Survival Data → Cox/KM → Synthesise
    (named "pipeline" to distinguish it from the console's own 6-step clinical flow: Case → Profile → Evidence → Score → Why → Options)
26. **GEOClient: Accessing 200K+ Datasets from NCBI GEO**
27. **GEOLoaderService: Parsing Expression Matrices**
28. **GEOSurvivalWorkflowOrchestrator: Pipeline Coordinator**
29. **GEORankingService: Selecting the Best Datasets**
30. **Gene Mapping: The Platform Babel Problem**
31. **Gene Mapping: Caching Makes It Possible**
32. **Statistical Engine: lifelines** — two-column: methods vs. data flow
33. **SurvivalAnalysisService: Statistical Core**

**AI Chat (slides 34–37)**

34. **AI Chat: pydantic-ai + RAG + Domain Score** — layered architecture overview
35. **AI Chat: 5 Tools Grounding Every Response in Real Data**
36. **RAG: Retrieval-Augmented Generation with numpy**
37. **Domain Score: This App vs Generic AI Chat**

**Cross-Cutting Concerns (slides 38–43)**

38. **End-to-End SSE Pipeline: From Query to Live Results**
39. **JWT Authentication: Stateless Security**
40. **Full Data Pipeline: NL Query → Publication Export**
41. **Multi-Layer Caching: Architecture Overview**
42. **asyncio.gather: The 10× Speedup in Practice**
43. **Error Handling: Resilient by Design**

**Engineering Decisions (slides 44–47)**

44. **SQLite vs PostgreSQL: Cost vs Capability**
45. **CI/CD Pipeline: From git push to Live**
46. **Server Setup: One-Time Steps** — 6-step workflow (Hetzner, Docker, DNS, secrets, Caddy TLS)
47. **Why Hetzner? Why Spaceship?** — two-column: server vendor vs. domain registrar rationale

**Demo (slides 48–50)**

48. **Demo: The Case Is the Query** — clinical console entry page + answerable-question catalogue
49. **Demo: Risk Scoring and What Drove It** — C-index tiles, reference KM by risk group, covariate contributions
50. **Demo: Treatments to Consider (Advisory)** — treated-vs-untreated cohort curves + CIViC/DGIdb evidence table

**Lessons Learned (slide 51)**

51. **What We Learned** — 2×3 grid of gap cards (asyncio.gather, hybrid metadata detection, disk-first caching, uv in Docker, RAG at query time, pydantic-ai)

## Screenshots

Place screenshots in `presentations/screenshots/` or a dated subfolder (e.g. `260123/`).
Required files: `app_entry_page.png`, `patient_scoring.png`, `treatments_prediction.png`.
Images are aspect-fitted into a 12.333 × 5.22 in box, so wide and near-square screenshots both work.
The script searches dated subdirectories newest-first, then falls back to the root screenshots folder.

## Editing Slides

Edit `scripts/create_presentation.py`. Slide order is built in `_build_slide_list()` (bottom of the file) as an ordered list of `add_*_slide(prs, ...)` closures — list position (1-based) is the slide number, one section at a time, matching the section groupings in Slide Structure above. `create_presentation()` builds all of them by default, or a subset via `slide_numbers` (see `--slides` above).

Reusable layout helpers (used for more than one slide):

| Function                  | Used for slides            |
|----------------------------|-----------------------------|
| `add_title_slide`          | 1                           |
| `add_two_col_slide`        | 8, 9, 32, 47                |
| `add_gap_cards_slide`      | 10, 51                      |
| `add_workflow_slide`       | 25, 46                      |
| `add_image_slide`          | 48, 49, 50                  |
| `add_architecture_slide`   | 34                          |

Every other slide (2–7, 11–24, 26–31, 33, 35–45) is generated by its own dedicated, single-purpose function named `add_<topic>_slide` (e.g. `add_fastapi_slide`, `add_rag_slide`, `add_mistral_slide`, `add_uv_slide`) — the function name and its `_title_block(...)` call match the slide title in the table above, so `grep -n "^def add_\|_title_block(slide," scripts/create_presentation.py` finds any slide's source fast.

Read `.claude/skills/pptx/references/helpers.md` for full parameter documentation.

After editing, open `presentations/app_presentation.pptx` to verify visually — pptx layout issues are only visible in the rendered file.
