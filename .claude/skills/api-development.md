# API Development Skill

Use this skill when creating or modifying FastAPI endpoints, Pydantic models, or API services for this project. Includes patterns for async operations and error handling.

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

## FastAPI Patterns

### Route Definition
```python
from fastapi import APIRouter, HTTPException, Depends
from app.models.request_models import AnalysisRequest
from app.models.response_models import AnalysisResponse

router = APIRouter(prefix="/api")

@router.post("/search", response_model=AnalysisResponse)
async def search_datasets(request: AnalysisRequest) -> AnalysisResponse:
    """
    Search GEO datasets and perform survival analysis.

    - **query**: Natural language search query
    - **max_datasets**: Maximum datasets to analyze (default: 10)
    - **model**: LLM model to use for ranking (default: mistral)
    """
    orchestrator = GEOSurvivalWorkflowOrchestrator()
    return await orchestrator.execute(request)

@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}
```

### Pydantic Models
```python
from pydantic import BaseModel, Field
from typing import Optional

class AnalysisRequest(BaseModel):
    """Request model for survival analysis."""
    query: str = Field(..., description="Natural language search query")
    max_datasets: int = Field(default=10, ge=1, le=50)
    organism: Optional[str] = Field(default=None)
    min_occurrence: int = Field(default=2, ge=1)
    model: str = Field(default="mistral")
    ranking_multiplier: int = Field(default=3, ge=1, le=10)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "breast cancer survival BRCA1",
                    "max_datasets": 5,
                    "model": "mistral"
                }
            ]
        }
    }

class GeneResult(BaseModel):
    """Individual gene survival result."""
    gene_symbol: str
    hazard_ratio: float
    p_value: float
    ci_lower: float
    ci_upper: float
    datasets_count: int
    direction: str  # "risk" or "protective"

class AnalysisResponse(BaseModel):
    """Response model for survival analysis."""
    query: str
    datasets_analyzed: int
    genes: list[GeneResult]
```

### Error Handling
```python
from fastapi import HTTPException
import httpx

async def fetch_dataset(dataset_id: str) -> dict:
    """Fetch dataset with proper error handling."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{GEO_API_URL}/{dataset_id}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Dataset {dataset_id} not found"
            )
        raise HTTPException(
            status_code=502,
            detail=f"GEO API error: {e.response.status_code}"
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Timeout fetching dataset {dataset_id}"
        )
```

### Dependency Injection
```python
from functools import lru_cache

class Settings(BaseModel):
    mistral_key: str
    email: str
    debug: bool = False

@lru_cache
def get_settings() -> Settings:
    return Settings(
        mistral_key=os.getenv("MISTRAL_KEY", ""),
        email=os.getenv("EMAIL", ""),
        debug=os.getenv("DEBUG", "false").lower() == "true"
    )

@router.post("/search")
async def search(
    request: AnalysisRequest,
    settings: Settings = Depends(get_settings)
) -> AnalysisResponse:
    # Use settings.mistral_key, etc.
    ...
```

## Service Layer Pattern

```python
import logging
from typing import Optional

class SurvivalAnalysisService:
    """Service for performing survival analysis."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

    async def analyze_dataset(
        self,
        dataset_id: str,
        expression_data: pd.DataFrame,
        survival_data: pd.DataFrame,
    ) -> list[GeneResult]:
        """Analyze all genes in a dataset."""
        self.logger.info(f"Analyzing dataset {dataset_id}")

        results = []
        for gene in expression_data.columns:
            try:
                result = await self._analyze_gene(
                    gene, expression_data, survival_data
                )
                results.append(result)
            except ValueError as e:
                self.logger.warning(f"Skipping {gene}: {e}")

        return results
```

## Async Patterns

### Parallel Execution
```python
import asyncio

async def analyze_multiple_datasets(
    dataset_ids: list[str]
) -> list[AnalysisResult]:
    """Analyze multiple datasets in parallel."""
    tasks = [analyze_dataset(did) for did in dataset_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out failed results
    return [r for r in results if not isinstance(r, Exception)]
```

### Rate-Limited Concurrency
```python
from asyncio import Semaphore

class RateLimitedClient:
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = Semaphore(max_concurrent)

    async def fetch(self, url: str) -> dict:
        async with self.semaphore:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                return response.json()
```

## Testing Endpoints

```bash
# Health check
curl http://localhost:8000/api/health

# Search with POST
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "lung cancer survival", "max_datasets": 3}'

# View OpenAPI docs
open http://localhost:8000/docs
```

## Logging Best Practices

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Detailed debugging info")
logger.info(f"Processing dataset {dataset_id}")
logger.warning(f"Low event count in {dataset_id}: {n_events}")
logger.error(f"Failed to fetch {dataset_id}: {error}")

# Include context
logger.info(
    "Analysis complete",
    extra={
        "dataset_id": dataset_id,
        "genes_analyzed": len(genes),
        "duration_seconds": elapsed
    }
)
```
