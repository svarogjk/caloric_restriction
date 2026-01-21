# Claude Code Project Instructions

> This file provides Claude Code-specific instructions. For general AI assistant guidelines, see `.github/copilot-instructions.md`.

## Quick Reference

- **Backend:** Python 3.13+, FastAPI, lifelines (survival analysis)
- **Frontend:** React 18, TypeScript, Redux Toolkit, Tailwind
- **Package Manager:** `uv` (backend), `npm` (frontend)

## Critical Rules

1. **No bare exceptions** - Always catch specific exception types or don't use try/except
2. **Use `uv run`** - Prefix all Python commands with `uv run`
3. **No standalone .md files** - Don't create explanation documents
4. **Async first** - Use async/await for all I/O operations

## Commands

```bash
# Backend
cd backend && uv run python -m uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Both (from project root)
cd backend && uv run python -m uvicorn app.main:app --reload &
cd frontend && npm run dev
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/api/routes.py` | API endpoints |
| `backend/app/services/survival_analysis_service.py` | Core survival analysis |
| `backend/app/services/geo_survival_workflow_orchestrator.py` | Main workflow |
| `frontend/src/store/searchSlice.ts` | Redux state |
| `frontend/src/services/api.ts` | API client |

## Domain Context

This app performs **survival analysis** on gene expression data from **GEO** (Gene Expression Omnibus). Key concepts:

- **Kaplan-Meier curves**: Survival probability over time
- **Cox regression**: Hazard ratios showing gene-survival associations
- **HR > 1**: Gene expression increases risk
- **HR < 1**: Gene expression is protective

## Code Patterns

### Adding a Service Method
```python
async def new_analysis_method(
    self,
    data: pd.DataFrame,
    parameters: AnalysisParams,
) -> AnalysisResult:
    """Brief description."""
    # Implementation
```

### Adding a Component
```typescript
interface Props {
  data: DataType;
  onAction: () => void;
}

export const NewComponent: React.FC<Props> = ({ data, onAction }) => {
  return <div>...</div>;
};
```

## Skills

Before working on these domains, read the corresponding skill file for project-specific patterns:

| Domain | Skill File | Trigger Keywords |
|--------|------------|------------------|
| Survival analysis | `.github/skills/survival-analysis/SKILL.md` | Kaplan-Meier, Cox, hazard ratio, lifelines |
| GEO data | `.github/skills/geo-data/SKILL.md` | GEO, GSE, expression matrix, probe mapping |
| API endpoints | `.github/skills/api-development/SKILL.md` | FastAPI, routes, endpoint, Pydantic |
| React frontend | `.github/skills/react-frontend/SKILL.md` | component, Redux, Tailwind, Recharts |

## Environment Variables

Required in `backend/.env`:
```
MISTRAL_KEY=your_key
EMAIL=your_email@example.com
```
