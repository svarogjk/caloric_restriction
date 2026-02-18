# FastAPI Exercises

Exercises based on patterns from `backend/app/api/routes.py`, `backend/app/services/`, and `backend/app/models/`.

## Beginner

### Exercise 1: Health Check Endpoint
**Task**: Create a GET endpoint at `/api/health` that returns a Pydantic response model with `status`, `version`, `timestamp` (ISO format), and `uptime_seconds` fields.
**Starter code**:
```python
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api")

# TODO: Define HealthResponse model with status (str), version (str),
#       timestamp (str), uptime_seconds (float)

# TODO: Define GET endpoint at "/health" with response_model=HealthResponse
```
**Test criteria**:
- Returns 200 with JSON matching HealthResponse schema
- `status` equals "healthy", `timestamp` is valid ISO datetime
**Key concepts**: APIRouter, Pydantic BaseModel, response_model, type annotations

### Exercise 2: Request Model with Validation
**Task**: Create a `GeneSearchRequest` Pydantic model with: `query` (str, 1-500 chars), `max_results` (int, 1-100, default 20), `organism` (Optional[str]), `significance_threshold` (float, 0-1, default 0.05). Use `Field()` with descriptions.
**Starter code**:
```python
from pydantic import BaseModel, Field
from typing import Optional

# TODO: Define GeneSearchRequest with Field() constraints and descriptions
# TODO: Define GeneSearchResponse with query, total_results, genes list
# TODO: Create POST endpoint at "/genes/search"
```
**Test criteria**:
- Rejects empty query, query > 500 chars, max_results outside 1-100
- Applies defaults correctly, field descriptions in OpenAPI schema
**Key concepts**: Pydantic Field, validation constraints (ge, le, min_length), Optional, defaults

## Intermediate

### Exercise 3: Service with Dependency Injection
**Task**: Build a `DatasetService` class that accepts an async database session, provides `get_by_id` and `list_recent` methods, and is injected into endpoints via `Depends()`.
**Starter code**:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

class DatasetService:
    # TODO: __init__ with session: AsyncSession
    # TODO: async get_by_id(dataset_id: str) -> Optional[dict]
    # TODO: async list_recent(limit: int = 20) -> list[dict]
    pass

# TODO: async def get_dataset_service(db: AsyncSession = Depends(get_db)) -> DatasetService
# TODO: GET endpoint "/datasets/{dataset_id}" using Depends(get_dataset_service)
```
**Test criteria**:
- DI chain works: get_db -> get_dataset_service -> endpoint
- 404 when dataset not found, response matches schema
**Key concepts**: Depends(), service layer, async dependency chain, HTTPException

### Exercise 4: Error Handling with httpx
**Task**: Build an async API client with proper error handling: catch `httpx.HTTPStatusError` (map 404 to 404, others to 502), `httpx.TimeoutException` (map to 504), rate limiting with asyncio.Semaphore, and retry with exponential backoff.
**Starter code**:
```python
import httpx, asyncio, logging
from typing import Optional

class GeneAPIClient:
    BASE_URL = "https://api.example.com/genes"
    # TODO: __init__ with api_key, rate_limit_delay, semaphore
    # TODO: async _rate_limit() - enforce delay between requests
    # TODO: async fetch_gene(gene_id: str) -> Optional[dict] - with retry
    # TODO: async fetch_batch(gene_ids: list[str]) -> list[dict] - concurrent with semaphore
```
**Test criteria**:
- Rate limiting enforces delay, retries on timeout with backoff
- Returns None on failure (doesn't raise), semaphore limits concurrency
**Key concepts**: httpx.AsyncClient, rate limiting, retry, asyncio.Semaphore, asyncio.gather

## Advanced

### Exercise 5: Workflow Orchestrator
**Task**: Build an `AnalysisOrchestrator` that coordinates: search → rank → analyze → aggregate. Each step delegates to a service. Use asyncio.gather with timeout for parallel analysis, Semaphore for concurrency control, and Counter for gene aggregation.
**Starter code**:
```python
import asyncio
from dataclasses import dataclass
from collections import Counter

class AnalysisOrchestrator:
    # TODO: __init__ accepting search_service, ranking_service, analysis_service
    # TODO: async run_pipeline(query, max_datasets, min_occurrence) -> PipelineResult
    #   Step 1: search with ranking_multiplier * max_datasets
    #   Step 2: rank and take top max_datasets
    #   Step 3: analyze_all with Semaphore(2) and wait_for(timeout=300)
    #   Step 4: find_common_genes using Counter with min_occurrence filter
```
**Test criteria**:
- Pipeline completes with mock services, timeout doesn't crash pipeline
- Common genes correctly counted with min_occurrence, semaphore limits concurrency
**Key concepts**: Orchestrator pattern, asyncio.Semaphore, wait_for, gather, Counter

### Exercise 6: Rate-Limited Paginated Fetcher
**Task**: Build a `RateLimitedFetcher` that fetches paginated API data: fetch page 1 to get total count, then fetch remaining pages concurrently with rate limiting and retry logic. Aggregate all results into a single `FetchResult`.
**Starter code**:
```python
import httpx, asyncio, time

class RateLimitedFetcher:
    # TODO: __init__ with base_url, requests_per_second, max_concurrent, max_retries
    # TODO: async _rate_limit() - enforce delay
    # TODO: async _fetch_page(endpoint, params, page, page_size) -> Optional[dict]
    # TODO: async fetch_all(endpoint, params, page_size, max_pages) -> FetchResult
    #   1. Fetch first page for total_count
    #   2. Calculate remaining pages
    #   3. Fetch remaining with asyncio.gather
    #   4. Return aggregated FetchResult
```
**Test criteria**:
- Rate limiting enforced, concurrent requests limited by semaphore
- Pagination calculates pages correctly, errors collected not raised
**Key concepts**: Pagination, rate limiting, asyncio.gather, exponential backoff
