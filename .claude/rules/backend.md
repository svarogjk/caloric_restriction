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

## In-Memory Cache Pattern

Use `collections.OrderedDict` (stdlib) for bounded LRU caches — no extra dependencies:

```python
from collections import OrderedDict

self._cache: OrderedDict[str, Value] = OrderedDict()
self._CACHE_MAX = 50

def _cache_get(self, key: str) -> Optional[Value]:
    if key in self._cache:
        self._cache.move_to_end(key)
        return self._cache[key]
    return None

def _cache_put(self, key: str, value: Value) -> None:
    self._cache[key] = value
    self._cache.move_to_end(key)
    if len(self._cache) > self._CACHE_MAX:
        self._cache.popitem(last=False)
```

Persist small lookup caches as JSON in `backend/platform_mappings/`. Never use `/tmp` for any project cache file.
