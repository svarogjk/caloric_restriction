# GEO Survival Analysis

> Cross-dataset biomarker discovery from NCBI GEO — no coding required.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19300334.svg)](https://doi.org/10.5281/zenodo.19300334)

Run a natural language query. Get a ranked, cross-validated list of survival-associated genes backed by independent cohorts, complete with Kaplan-Meier curves, forest plots, hazard ratios, and a publication-ready export — in under 5 minutes.

<!-- Add demo GIF here: docs/demo.gif -->

---

## Why This Exists

Tools like KMplot, GEPIA2, and OncoLnc are locked to curated databases (TCGA, GTEx). When your cancer type isn't represented, or you need **independent validation across multiple cohorts**, they fall short.

GEO Survival Analysis searches the entire NCBI GEO archive (thousands of studies) and performs cross-cohort meta-analysis automatically. A gene significant in 8 independent datasets carries far more weight than one significant in a single well-powered study.

| Tool | Data Source | Cross-Cohort Meta-Analysis | Natural Language Input |
|---|---|---|---|
| KMplot | TCGA + curated | No | No |
| GEPIA2 | TCGA + GTEx | No | No |
| OncoLnc | TCGA only | No | No |
| **GEO Survival Analysis** | **All of GEO** | **Yes** | **Yes** |

---

## Features

- **Natural language queries** — "lung adenocarcinoma survival" finds and analyzes relevant GEO datasets automatically
- **Cross-dataset meta-analysis** — ranks genes by consistency across independent cohorts, not just one study
- **Kaplan-Meier curves** with confidence intervals, per-dataset and combined views
- **Forest plots** showing per-dataset hazard ratios with pooled effect and heterogeneity statistics (I²)
- **Volcano plot** — interactive HR vs. significance scatter with clickable genes
- **Real-time progress** — SSE streaming shows dataset download and analysis stages live
- **Gene batch mode** — paste up to 500 gene symbols to restrict analysis to your candidate list
- **COSMIC cancer gene filter** — restrict to ~600 well-characterised cancer driver genes
- **CSV + PNG export** — download gene tables and plots directly from the UI
- **Shareable permalinks** — `/results/:id` renders results publicly, no login required
- **Analysis history** — saved results with reloadable views
- **Publication export** — ZIP package with genes.csv, per-dataset results, and a pre-written Methods paragraph
- **AI chat assistant** — ask follow-up questions about results, get biological context
- **Analysis comparison** — side-by-side view of two independent analyses

---

## Quick Start

### Prerequisites

- Python 3.13+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- Mistral API key (for embeddings and default LLM)
- Anthropic API key (optional, for Claude model)
- PostgreSQL 15+ (optional; SQLite is the default database)

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_ORG/geo-survival-analysis.git
cd geo-survival-analysis
```

Create `backend/.env`:

```env
MISTRAL_KEY=your_mistral_key_here
JWT_SECRET_KEY=your_secret_key_here
EMAIL=your_email@example.com
# Optional: set DATABASE_URL to use PostgreSQL instead of SQLite
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/geo_survival
```

### 2. Run migrations

```bash
cd backend
uv run alembic upgrade head
```

### 4. Start the backend

```bash
cd backend
uv run python -m uvicorn app.main:app --reload --port 8000
```

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## Example Query

```
lung adenocarcinoma overall survival
```

The tool will:
1. Search NCBI GEO for relevant datasets
2. Download and parse expression matrices
3. Map probe IDs to gene symbols
4. Run Cox regression and log-rank tests on each dataset
5. Rank genes by cross-cohort consistency
6. Return results with KM curves, forest plots, and HRs

Typical runtime: **2–5 minutes** for 10 datasets.

---

## Architecture

```
frontend/          React 18 + TypeScript + Redux Toolkit + Recharts
backend/
  app/
    api/           FastAPI routers (analysis, chat, auth, export)
    services/      Orchestrator, survival analysis, GEO client, RAG
    models/        SQLAlchemy ORM + Pydantic request/response models
    config/        Database, settings, logging
```

**Key dependencies:**
- [lifelines](https://lifelines.readthedocs.io/) — Cox regression, Kaplan-Meier estimator
- [pydantic-ai 1.x](https://ai.pydantic.dev/) — AI chat agent with tool calling
- numpy — in-memory cosine similarity RAG over Mistral embeddings
- [FastAPI](https://fastapi.tiangolo.com/) — async REST API with SSE streaming

---

## Statistical Methods

Gene expression is split into **high** and **low** groups at the per-dataset median. Survival analysis uses:

- **Cox proportional hazards regression** (`lifelines.CoxPHFitter`) — hazard ratio + 95% CI per dataset
- **Log-rank test** — independent significance test per dataset
- **Cross-cohort ranking** — genes ranked by number of significant datasets, then by average p-value
- **Heterogeneity** — Cochran Q statistic and I² reported on forest plots

A gene is included in results when it meets the significance threshold (p < 0.05) in at least `min_occurrence` datasets (default: 2).

---

## API

The backend exposes a REST API at `http://localhost:8000/api`.

```http
POST   /api/search                    Run analysis (blocking)
GET    /api/search/stream             Run analysis with SSE progress
GET    /api/results/{id}              Get saved result (public)
GET    /api/results/{id}/export       Download publication ZIP
GET    /api/results                   List user's saved results
POST   /api/results                   Save a result explicitly
GET    /api/health                    Health check
```

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Roadmap

- [x] Kaplan-Meier curves with CI bands
- [x] Forest plots with heterogeneity statistics
- [x] CSV + PNG export
- [x] Real-time analysis progress (SSE)
- [x] Shareable result permalinks
- [x] Gene batch input mode
- [x] Analysis history dashboard
- [x] Publication export package (ZIP)
- [x] Analysis comparison mode
- [x] AI chat with RAG context
- [ ] Pathway / GO enrichment (F11)
- [ ] Multivariate Cox regression (F13)

---

## Citation

If you use GEO Survival Analysis in your research, please cite:

> Korkodnov I. et al. GEO Survival Analysis: cross-cohort biomarker discovery from NCBI GEO.
> *Nucleic Acids Research*, Web Server Issue, 2026.
> DOI: [10.5281/zenodo.19300334](https://doi.org/10.5281/zenodo.19300334)

---

## License

MIT — see [LICENSE](LICENSE).

---

## Contributing

Issues and PRs welcome. Please open an issue first for major changes.
