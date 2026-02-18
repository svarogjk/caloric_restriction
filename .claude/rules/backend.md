---
paths:
  - "backend/**/*"
---

# Backend Rules

Python 3.13+, FastAPI, lifelines, uv package manager.

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/api/routes.py` | API endpoints |
| `backend/app/services/survival_analysis_service.py` | Core survival analysis |
| `backend/app/services/geo_survival_workflow_orchestrator.py` | Main workflow |

## Architecture

```
routes.py (API layer) → services/ (business logic) → clients/ (external APIs)
```

## Patterns

- Async service methods with type hints: `async def method(self, data: pd.DataFrame) -> Result:`
- Endpoints use `Depends()` for service injection, Pydantic models for request/response
- Log appropriately: debug for flow, info for operations, warning/error for issues
- Handle errors with specific exception types
