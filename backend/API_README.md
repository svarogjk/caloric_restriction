# FastAPI GEO Analysis Server

FastAPI REST API for Gene Expression Omnibus (GEO) analysis workflow.

## Installation

```bash
cd backend
pip install -e .
```

## Running the Server

```bash
# Development mode with auto-reload
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Analyze GEO Data
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "caloric restriction aging",
    "max_datasets": 10,
    "organism": "Mus musculus",
    "min_occurrence": 2
  }'
```

### Quick Analysis (with defaults)
```bash
curl http://localhost:8000/analyze/quick
```

## Interactive API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Request Schema

```json
{
  "query": "caloric restriction aging",
  "max_datasets": 10,
  "organism": "Mus musculus",
  "min_occurrence": 2
}
```

## API Response Schema

```json
{
  "query": "caloric restriction aging",
  "n_datasets_analyzed": 10,
  "n_datasets_with_degs": 8,
  "common_genes": [
    {
      "gene_id": "ENSMUST00000001",
      "n_datasets": 5,
      "avg_log_fc": 1.2,
      "direction_consistency": 0.9,
      "datasets": ["GSE123", "GSE124"]
    }
  ],
  "processing_time": 45.3,
  "timestamp": "2025-11-14T12:00:00"
}
```

## Project Structure

```
backend/
├── app/
│   ├── main.py                      # FastAPI application
│   ├── models/
│   │   └── llm_models.py
│   └── services/
│       ├── geo_workflow_orchestrator.py    # Main orchestrator
│       ├── geo_client.py
│       ├── geo_loader_service.py
│       ├── geo_ranking_service.py
│       └── differential_expression_service.py
├── pyproject.toml                   # Dependencies
└── geo_cache/                       # Cache directory
```

## Features

- **Full-text search** of GEO datasets
- **Intelligent ranking** of datasets by DE analysis potential
- **Differential expression analysis** across multiple datasets
- **Common gene identification** across studies
- **CORS enabled** for cross-origin requests
- **Auto-generated API documentation** via Swagger UI

## Environment Variables

Configure the following in `app/main.py`:

- `EMAIL`: Email for GEO API (currently: "svarogjk1989@gmail.com")
- `MODEL`: LLM model to use (currently: "mistral")

## Performance

- Typical analysis: 1-2 minutes per query
- Caching enabled for loaded datasets
- Async/await for concurrent operations
