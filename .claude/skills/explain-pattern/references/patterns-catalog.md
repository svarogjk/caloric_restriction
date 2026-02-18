# Project Patterns Catalog

Architectural patterns used in this project with source file locations for real code examples.

## Orchestrator Pattern

**What**: A central coordinator that sequences multiple services to complete a complex workflow.
**Source files**:
- `backend/app/services/geo_survival_workflow_orchestrator.py` — Main orchestrator
- `backend/app/main.py` — Orchestrator initialization in app lifespan

**Key elements**:
- Single entry point (`analyze_query`) coordinates search → rank → load → analyze → aggregate
- Each step delegates to a specialized service
- Error handling at orchestrator level allows partial results
- Services are injected via constructor, enabling testing with mocks

**When to use**: When a workflow involves 3+ steps across different services that must execute in sequence.

## Service Layer Architecture

**What**: Routes handle HTTP concerns, services handle business logic, clients handle external I/O.
**Source files**:
- `backend/app/api/routes.py` — Route layer (HTTP request/response)
- `backend/app/api/chat_routes.py` — Chat route layer
- `backend/app/services/survival_analysis_service.py` — Service layer (business logic)
- `backend/app/services/geo_client.py` — Client layer (external API calls)

**Key elements**:
- Routes: parse request, call service, format response, handle HTTP errors
- Services: business logic, validation, transformation, no HTTP concerns
- Clients: external API calls, rate limiting, retries

**When to use**: Always. Every new feature should follow routes → services → clients.

## Async Patterns

**What**: Non-blocking I/O using Python's asyncio for concurrent operations.
**Source files**:
- `backend/app/services/geo_client.py` — Async HTTP client with httpx
- `backend/app/services/geo_survival_workflow_orchestrator.py` — Async workflow
- `backend/app/config/database.py` — Async database sessions

**Key elements**:
- `async with httpx.AsyncClient()` for HTTP calls
- `asyncio.gather()` for parallel execution
- `asyncio.Semaphore` for rate limiting
- `async_sessionmaker` for database sessions
- Never use synchronous I/O (requests, time.sleep, open) in async context

**When to use**: All I/O operations (HTTP, database, file). This is a project-wide rule.

## Redux State Management

**What**: Centralized state management using Redux Toolkit slices with async thunks.
**Source files**:
- `frontend/src/store/store.ts` — Store configuration
- `frontend/src/store/searchSlice.ts` — Search state (query, results, loading, error)
- `frontend/src/store/authSlice.ts` — Auth state with async thunks
- `frontend/src/store/chatSlice.ts` — Chat state

**Key elements**:
- `createSlice` defines state shape, reducers, and action creators
- `createAsyncThunk` handles API calls with pending/fulfilled/rejected lifecycle
- `extraReducers` maps thunk actions to state changes
- Immer enables "mutable" reducer syntax with immutable results
- `useSelector` + `useDispatch` hooks in components

**When to use**: Any state shared across components. Local UI state (toggles, form inputs) uses useState.

## Recharts Data Flow

**What**: Transform raw data into Recharts-compatible format using useMemo, then render composable chart components.
**Source files**:
- `frontend/src/components/KaplanMeierPlot.tsx` — Step-function line chart
- `frontend/src/components/VolcanoPlot.tsx` — Scatter chart with color coding

**Key elements**:
- `useMemo` transforms API response data into chart-ready arrays
- Recharts composable API: `<LineChart>`, `<XAxis>`, `<YAxis>`, `<Tooltip>`, `<Legend>`
- `type="stepAfter"` for survival curves (flat-then-drop)
- Color functions map data values to visual properties (risk levels → red/blue/gray)
- `<ResponsiveContainer>` for responsive sizing

**When to use**: Any data visualization. Follow the pattern: transform → memoize → render.

## JWT Authentication Flow

**What**: Full-stack authentication using JWT tokens with Argon2 password hashing.
**Source files**:
- `backend/app/services/auth_service.py` — Password hashing, token creation
- `backend/app/api/auth_routes.py` — Login, register, token endpoints
- `backend/app/api/dependencies.py` — `get_current_user` dependency
- `frontend/src/services/authApi.ts` — Auth API client
- `frontend/src/store/authSlice.ts` — Auth state management
- `frontend/src/services/api.ts` — Axios interceptors for token injection
- `frontend/src/components/auth/AuthGuard.tsx` — Protected route wrapper

**Key elements**:
- Backend: Argon2 hash → JWT create → OAuth2PasswordBearer dependency
- Frontend: login → store token in localStorage → Axios interceptor adds Bearer header
- 401 response → interceptor removes token → redirect to login
- `AuthGuard` wrapper component checks `isAuthenticated` before rendering children

**When to use**: Any endpoint that requires user identity. Add `Depends(get_current_active_user)`.

## LLM Agent with Fallback

**What**: Use an LLM agent for intelligent data detection, with regex fallback for reliability.
**Source files**:
- `backend/app/services/survival_analysis_service.py` — Detection agent + regex fallback

**Key elements**:
- Primary: pydantic-ai `Agent` with structured output (`SurvivalDataDetectionResponse`)
- Fallback: Regex patterns matching common column names (e.g., "os_time", "survival_days")
- Graceful degradation: if LLM fails, regex still provides reasonable results
- Structured output ensures type safety (Pydantic model validation)

**When to use**: When you need intelligent parsing of unstructured data but must guarantee a result.

## Pydantic Model Configuration

**What**: Pydantic v2 models for API request/response validation with rich configuration.
**Source files**:
- `backend/app/models/request_models.py` — Request models with Field constraints
- `backend/app/models/response_models.py` — Response models
- `backend/app/schemas/auth.py` — Auth schemas

**Key elements**:
- `Field(...)` with `description`, `ge`, `le`, `default` for validation
- `model_config` with `json_schema_extra` for OpenAPI examples
- Nested models for complex responses
- Separate request and response models (different shapes for input/output)

**When to use**: All API boundaries. Requests get validated, responses get serialized.

## FastAPI Dependency Injection

**What**: Inject shared resources (settings, DB sessions, auth) into route handlers.
**Source files**:
- `backend/app/api/dependencies.py` — Auth dependencies
- `backend/app/config/settings.py` — Settings with `@lru_cache`
- `backend/app/config/database.py` — Database session factory

**Key elements**:
- `Depends(get_settings)` for configuration
- `Depends(get_db)` for async database sessions
- `Depends(get_current_user)` for authentication
- `@lru_cache` on settings factory for singleton behavior
- Dependencies can depend on other dependencies (chaining)

**When to use**: When a route handler needs external resources. Never import globals directly.

## SQLAlchemy Async Session Management

**What**: Async database sessions with proper lifecycle management.
**Source files**:
- `backend/app/config/database.py` — Engine and session factory
- `backend/app/models/database.py` — ORM models with relationships

**Key elements**:
- `create_async_engine()` with connection pooling (`pool_size=5`, `max_overflow=10`)
- `async_sessionmaker(expire_on_commit=False)` for session factory
- `AsyncSession` used with `async with` for automatic cleanup
- Smart database detection: PostgreSQL (production) → SQLite (development fallback)
- `mapped_column()` with type annotations for columns
- `relationship()` with `cascade="all, delete-orphan"` for parent-child

**When to use**: All database operations. Always use async sessions, never synchronous.

## Axios Interceptor Pattern

**What**: Automatic JWT token injection and 401 handling via Axios interceptors.
**Source files**:
- `frontend/src/services/api.ts` — Main API client with interceptors
- `frontend/src/services/authApi.ts` — Auth-specific API client

**Key elements**:
- Request interceptor: reads token from localStorage, adds `Authorization: Bearer` header
- Response interceptor: catches 401 errors, removes stored token, dispatches logout
- Base URL configuration for API proxy
- Separate API instances for auth vs data endpoints

**When to use**: Already configured globally. New API calls automatically get auth headers.

## Survival Analysis Pipeline

**What**: Multi-step pipeline for gene expression survival analysis.
**Source files**:
- `backend/app/services/survival_analysis_service.py` — Full pipeline

**Key elements**:
1. Detect survival columns (LLM agent + regex fallback)
2. Extract survival data (flexible format parsing)
3. For each gene: median split → high/low groups → log-rank test → Cox regression
4. Aggregate results: average HR across datasets, consistency scoring
5. Validation: minimum events (10), expression variance > 0, FDR correction

**When to use**: When adding new analysis types or modifying the survival pipeline.
