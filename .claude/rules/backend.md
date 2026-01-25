# Backend Rules

Python 3.13+, FastAPI, lifelines, uv package manager.

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/api/routes.py` | API endpoints |
| `backend/app/services/survival_analysis_service.py` | Core survival analysis |
| `backend/app/services/geo_survival_workflow_orchestrator.py` | Main workflow |

## Commands

```bash
# Start dev server
cd backend && uv run python -m uvicorn app.main:app --reload --port 8000

# Run tests
cd backend && uv run pytest

# Type check
cd backend && uv run mypy app/
```

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

### API Endpoint Pattern
```python
@router.post("/endpoint", response_model=ResponseModel)
async def endpoint_name(
    request: RequestModel,
    service: ServiceClass = Depends(get_service),
) -> ResponseModel:
    """Endpoint description."""
    result = await service.do_work(request.data)
    return ResponseModel(data=result)
```

### Service Layer Architecture
```
routes.py (API layer)
    ↓
services/ (business logic)
    ↓
clients/ (external APIs)
```

## Requirements

- All functions must have type hints
- Use Pydantic models for request/response validation
- Log appropriately (debug, info, warning, error)
- Handle errors with specific exception types
