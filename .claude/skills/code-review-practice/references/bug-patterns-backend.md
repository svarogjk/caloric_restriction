# Bug Patterns - Backend (Python/FastAPI)

Bug templates for generating code review exercises. Each pattern includes the buggy code, the fix, and the category.

## Security Bugs

### Bare Exception
```python
# BUGGY
try:
    result = await service.analyze(data)
except:
    return {"error": "failed"}

# FIX
except ValueError as e:
    logger.error(f"Validation error: {e}")
    raise HTTPException(status_code=400, detail=str(e))
```
**Impact**: Silently swallows all errors including SystemExit, KeyboardInterrupt. Violates project rule: no bare exceptions.

### Hardcoded Secret
```python
# BUGGY
JWT_SECRET = "my-super-secret-key-2024"
token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# FIX
JWT_SECRET = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET_KEY not set")
```
**Impact**: Secrets in source code are exposed in git history. Always use environment variables.

### SQL Injection via f-string
```python
# BUGGY
query = f"SELECT * FROM users WHERE username = '{username}'"
result = await session.execute(text(query))

# FIX
result = await session.execute(
    text("SELECT * FROM users WHERE username = :username"),
    {"username": username}
)
```
**Impact**: Allows attackers to execute arbitrary SQL. Always use parameterized queries.

### Missing Auth Check
```python
# BUGGY
@router.delete("/users/{user_id}")
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
    await db.delete(user)

# FIX
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
```
**Impact**: Anyone can delete any user without authentication. Always use auth dependencies.

### Unsafe Deserialization
```python
# BUGGY
import pickle
data = pickle.loads(request_body)

# FIX
data = json.loads(request_body)
validated = PydanticModel.model_validate(data)
```
**Impact**: Pickle deserialization can execute arbitrary code. Use JSON + Pydantic validation.

## Logic Bugs

### Wrong Async Usage
```python
# BUGGY
def fetch_data(url: str):
    response = requests.get(url)  # Synchronous in async context
    return response.json()

# FIX
async def fetch_data(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```
**Impact**: Blocks the event loop, degrading performance for all concurrent requests.

### Missing Await
```python
# BUGGY
async def get_analysis():
    result = service.analyze_dataset(data)  # Missing await
    return result

# FIX
async def get_analysis():
    result = await service.analyze_dataset(data)
    return result
```
**Impact**: Returns a coroutine object instead of the actual result. May cause TypeErrors downstream.

### Off-by-One in Pagination
```python
# BUGGY
results = items[offset:offset + limit + 1]  # Returns one extra

# FIX
results = items[offset:offset + limit]
```
**Impact**: Returns one more item than requested, breaking pagination.

### Wrong Comparison for Floating Point
```python
# BUGGY
if p_value == 0.05:
    significant = True

# FIX
if p_value <= 0.05:
    significant = True
# Or for equality: abs(p_value - 0.05) < 1e-10
```
**Impact**: Floating point comparisons with `==` are unreliable. Use `<=` or epsilon comparison.

### Mutable Default Argument
```python
# BUGGY
def analyze_genes(genes: list[str], results: list = []):
    results.append(analyze(genes[0]))
    return results

# FIX
def analyze_genes(genes: list[str], results: list | None = None):
    if results is None:
        results = []
```
**Impact**: Mutable defaults are shared across calls, accumulating state.

## Performance Bugs

### N+1 Query Pattern
```python
# BUGGY
conversations = await session.execute(select(Conversation))
for conv in conversations.scalars():
    messages = await session.execute(
        select(Message).where(Message.conversation_id == conv.id)
    )

# FIX
stmt = select(Conversation).options(selectinload(Conversation.messages))
conversations = await session.execute(stmt)
```
**Impact**: Executes N+1 database queries instead of 1-2 with eager loading.

### Blocking I/O in Async
```python
# BUGGY
async def read_large_file(path: str):
    with open(path) as f:
        return f.read()  # Blocks event loop

# FIX
async def read_large_file(path: str):
    import aiofiles
    async with aiofiles.open(path) as f:
        return await f.read()
```
**Impact**: File I/O blocks the event loop. Use `aiofiles` or `asyncio.to_thread()`.

### Creating Client Per Request
```python
# BUGGY
async def fetch(url):
    async with httpx.AsyncClient() as client:  # New client each call
        return await client.get(url)

# FIX: Reuse client instance
class Service:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
```
**Impact**: TCP connection overhead per request. Reuse clients for connection pooling.

### Unnecessary Serialization
```python
# BUGGY
data = json.loads(json.dumps(dataframe.to_dict()))

# FIX
data = dataframe.to_dict(orient="records")
```
**Impact**: Double serialization wastes CPU. Convert directly to the target format.

## Style/Convention Bugs

### Missing Type Hints
```python
# BUGGY
def process(data, threshold):
    return [x for x in data if x > threshold]

# FIX
def process(data: pd.Series, threshold: float) -> list[float]:
    return [x for x in data if x > threshold]
```
**Impact**: Reduces code readability and IDE support. Project requires type hints.

### Wrong Import Style
```python
# BUGGY
from fastapi import *

# FIX
from fastapi import APIRouter, HTTPException, Depends
```
**Impact**: Wildcard imports pollute namespace and make dependencies unclear.

### Missing Logging
```python
# BUGGY
async def analyze(data):
    result = compute(data)
    return result

# FIX
async def analyze(data):
    logger.info(f"Starting analysis with {len(data)} records")
    result = compute(data)
    logger.info(f"Analysis complete: {len(result)} results")
    return result
```
**Impact**: Without logging, debugging production issues is nearly impossible.

### Direct Attribute Access Without Validation
```python
# BUGGY
gene_name = response["data"]["genes"][0]["name"]

# FIX
data = response.get("data", {})
genes = data.get("genes", [])
gene_name = genes[0]["name"] if genes else None
```
**Impact**: Crashes with KeyError/IndexError on unexpected API responses.
