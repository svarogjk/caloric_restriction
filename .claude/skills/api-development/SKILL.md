---
name: api-development
description: FastAPI backend development patterns for this project. Use when creating or modifying API endpoints, Pydantic models, service layer code, or async patterns.
---

# API Development Patterns

## Project Structure

```
backend/app/
├── main.py                    # FastAPI app initialization
├── api/routes.py              # Endpoint definitions
├── models/
│   ├── request_models.py      # Pydantic request schemas
│   ├── response_models.py     # Pydantic response schemas
│   └── llm_models.py          # LLM integration models
└── services/                  # Business logic
```

## Route Pattern

```python
from fastapi import APIRouter, HTTPException, Depends

router = APIRouter(prefix="/api")

@router.post("/search", response_model=AnalysisResponse)
async def search_datasets(request: AnalysisRequest) -> AnalysisResponse:
    orchestrator = GEOSurvivalWorkflowOrchestrator()
    return await orchestrator.execute(request)
```

## Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import Optional

class AnalysisRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    max_datasets: int = Field(default=10, ge=1, le=50)
    organism: Optional[str] = Field(default=None)
    model: str = Field(default="mistral")

    model_config = {
        "json_schema_extra": {
            "examples": [{"query": "breast cancer survival BRCA1", "max_datasets": 5}]
        }
    }
```

## Error Handling

```python
async def fetch_dataset(dataset_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{GEO_API_URL}/{dataset_id}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
        raise HTTPException(status_code=502, detail=f"GEO API error: {e.response.status_code}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Timeout fetching dataset {dataset_id}")
```

## Service Layer

```python
class SurvivalAnalysisService:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

    async def analyze_dataset(
        self, dataset_id: str, expression_data: pd.DataFrame, survival_data: pd.DataFrame,
    ) -> list[GeneResult]:
        self.logger.info(f"Analyzing dataset {dataset_id}")
        results = []
        for gene in expression_data.columns:
            try:
                result = await self._analyze_gene(gene, expression_data, survival_data)
                results.append(result)
            except ValueError as e:
                self.logger.warning(f"Skipping {gene}: {e}")
        return results
```

## Async Patterns

```python
# Parallel execution
async def analyze_multiple(dataset_ids: list[str]) -> list[AnalysisResult]:
    tasks = [analyze_dataset(did) for did in dataset_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]

# Rate-limited concurrency
class RateLimitedClient:
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = Semaphore(max_concurrent)

    async def fetch(self, url: str) -> dict:
        async with self.semaphore:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                return response.json()
```

## Dependency Injection

```python
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings(mistral_key=os.getenv("MISTRAL_KEY", ""), email=os.getenv("EMAIL", ""))

@router.post("/search")
async def search(request: AnalysisRequest, settings: Settings = Depends(get_settings)):
    ...
```

## Testing

```bash
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "lung cancer survival", "max_datasets": 3}'
```
