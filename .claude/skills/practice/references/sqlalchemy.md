# SQLAlchemy Async Exercises

Exercises based on patterns from `backend/app/models/database.py` and `backend/app/config/database.py`.

## Beginner

### Exercise 1: Define a Model with Typed Columns
**Task**: Define a `GeneAnnotation` model with: `id` (UUID PK), `gene_symbol` (unique str), `description` (text), `organism` (str), `chromosome` (Optional[str]), `created_at` (datetime with default). Use `mapped_column()` with type annotations.
**Starter code**:
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    pass

class GeneAnnotation(Base):
    __tablename__ = "gene_annotations"
    # TODO: id - UUID primary key with default uuid4
    # TODO: gene_symbol - String(50), unique, not nullable, indexed
    # TODO: description - Text, nullable
    # TODO: organism - String(100), not nullable, default "Homo sapiens"
    # TODO: chromosome - Optional String(10)
    # TODO: created_at - DateTime with server default
```
**Test criteria**:
- Table has correct column types and constraints
- UUID auto-generated, created_at defaults to now, unique constraint on gene_symbol
**Key concepts**: DeclarativeBase, Mapped, mapped_column, column constraints

### Exercise 2: Basic Async Query
**Task**: Write async functions to: insert a record, query by ID, query by filter (organism), and count records. Use `async_sessionmaker` and proper session handling.
**Starter code**:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

# TODO: async def create_annotation(session: AsyncSession, gene_symbol: str, ...) -> GeneAnnotation
# TODO: async def get_by_id(session: AsyncSession, annotation_id: str) -> Optional[GeneAnnotation]
# TODO: async def find_by_organism(session: AsyncSession, organism: str) -> list[GeneAnnotation]
# TODO: async def count_annotations(session: AsyncSession) -> int
```
**Test criteria**:
- Create returns model instance with generated ID
- get_by_id returns None for missing records
- find_by_organism filters correctly, count returns integer
**Key concepts**: AsyncSession, select(), session.execute(), session.add(), session.commit()

## Intermediate

### Exercise 3: CRUD Service with Async Session
**Task**: Build a `GeneAnnotationService` class with full CRUD operations, pagination support, and search functionality. Follow the service layer pattern.
**Starter code**:
```python
class GeneAnnotationService:
    def __init__(self, session: AsyncSession):
        self.session = session
    # TODO: async create(data: dict) -> GeneAnnotation
    # TODO: async get(id: str) -> Optional[GeneAnnotation]
    # TODO: async list(offset: int, limit: int, organism: Optional[str]) -> list[GeneAnnotation]
    # TODO: async update(id: str, data: dict) -> Optional[GeneAnnotation]
    # TODO: async delete(id: str) -> bool
    # TODO: async search(query: str) -> list[GeneAnnotation] - search gene_symbol and description
```
**Test criteria**:
- CRUD operations work correctly with async sessions
- Pagination with offset/limit, optional organism filter
- Search uses ILIKE for case-insensitive matching
**Key concepts**: CRUD pattern, pagination, ILIKE search, session management

### Exercise 4: One-to-Many Relationship
**Task**: Define `Experiment` and `ExperimentResult` models with a one-to-many relationship. Include cascade delete, back-population, and eager loading via `selectinload`.
**Starter code**:
```python
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey

class Experiment(Base):
    __tablename__ = "experiments"
    # TODO: id, title, created_at columns
    # TODO: results relationship with cascade="all, delete-orphan", back_populates

class ExperimentResult(Base):
    __tablename__ = "experiment_results"
    # TODO: id, experiment_id (ForeignKey), gene_symbol, hazard_ratio, p_value
    # TODO: experiment relationship with back_populates

# TODO: async def get_experiment_with_results(session, exp_id) -> Experiment
#   Use selectinload to eagerly load results
```
**Test criteria**:
- Deleting experiment cascades to results
- selectinload loads results in single query
- Back-population works both directions
**Key concepts**: relationship(), ForeignKey, cascade, selectinload, back_populates

## Advanced

### Exercise 5: Soft Delete Pattern
**Task**: Create a `SoftDeleteMixin` that adds `deleted_at` column and overrides queries to exclude soft-deleted records. Include `soft_delete()`, `restore()`, and `hard_delete()` methods.
**Starter code**:
```python
class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    # TODO: @property is_deleted -> bool
    # TODO: async soft_delete(session) - set deleted_at = now
    # TODO: async restore(session) - set deleted_at = None

# TODO: Helper function active_query(model) that adds .where(model.deleted_at.is_(None))
# TODO: Apply to Conversation model and demonstrate filtered queries
```
**Test criteria**:
- soft_delete sets timestamp, is_deleted returns True
- restore clears timestamp, active_query excludes deleted records
- hard_delete permanently removes record
**Key concepts**: Mixins, soft delete, query filtering, datetime columns

### Exercise 6: Repository Pattern with Transactions
**Task**: Build a `Repository` base class with transaction management. Support `unit_of_work` context manager for atomic operations across multiple repositories.
**Starter code**:
```python
from contextlib import asynccontextmanager

class BaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

class ExperimentRepository(BaseRepository):
    # TODO: async create_with_results(experiment_data, results_data) -> Experiment
    #   Both must succeed or both roll back

# TODO: @asynccontextmanager async def unit_of_work(session_factory):
#   Yield session, commit on success, rollback on exception
```
**Test criteria**:
- Transaction commits all or nothing
- Rollback on any exception within unit_of_work
- Repository methods use shared session
**Key concepts**: Repository pattern, transactions, context manager, rollback
