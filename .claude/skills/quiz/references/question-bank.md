# Quiz Question Bank

## FastAPI

### Q: What is the correct way to make an HTTP call inside a FastAPI async endpoint?
- A) `requests.get(url)`
- B) `async with httpx.AsyncClient() as c: await c.get(url)` ✓
- C) `urllib.urlopen(url)`
- D) `http.client.HTTPConnection(url)`
**Explanation**: FastAPI endpoints are async. Using synchronous HTTP libraries like `requests` blocks the event loop. Use `httpx.AsyncClient` for non-blocking I/O. See `backend/app/services/geo_client.py` for examples.

### Q: How does FastAPI dependency injection work with `Depends()`?
- A) It creates a new instance every request ✓
- B) It creates a singleton shared across requests
- C) It only works with class-based dependencies
- D) It requires manual cleanup
**Explanation**: `Depends()` calls the dependency function per-request by default. For shared instances, combine with `@lru_cache`. See `backend/app/api/dependencies.py`.

### Q: What happens if a Pydantic model field has `Field(default=10, ge=1, le=50)`?
- A) The field is required with a default of 10
- B) The field is optional, defaults to 10, and validates range 1-50 ✓
- C) The field only accepts the value 10
- D) The field is required and must be between 1 and 50
**Explanation**: `default=10` makes it optional with a default. `ge=1, le=50` adds validation constraints. See `AnalysisRequest` in `backend/app/models/request_models.py`.

### Q: What's wrong with this error handling?
```python
except Exception:
    return {"error": "something went wrong"}
```
- A) Should use `except Exception as e` for logging
- B) Should catch specific exception types, not bare Exception ✓
- C) Should return an HTTPException instead
- D) Both B and C ✓
**Explanation**: Project rules require catching specific exception types (ValueError, httpx.HTTPStatusError, etc.), never bare `except:` or `except Exception`. See `.claude/rules/critical.md`.

### Q: What is the purpose of `response_model` in a FastAPI route decorator?
- A) It validates the request body
- B) It documents and validates the response shape ✓
- C) It creates a database model
- D) It defines the HTTP method
**Explanation**: `response_model` tells FastAPI to validate the response against the Pydantic model and generate OpenAPI docs. It also filters out extra fields not in the model.

## React/TypeScript

### Q: What is the correct way to type a functional component with props?
- A) `function Component(props: any)`
- B) `const Component: React.FC<Props> = ({ prop1 }) => ...` ✓
- C) `class Component extends React.Component`
- D) `function Component(props: Props)` ✓
**Explanation**: Both `React.FC<Props>` and typed function arguments work. This project uses `React.FC<Props>` with destructured props. `any` is forbidden by project rules. See `frontend/src/components/GeneCard.tsx`.

### Q: What does `useSelector((state: RootState) => state.search)` return?
- A) The entire Redux store
- B) The search slice state object ✓
- C) A dispatch function
- D) An action creator
**Explanation**: `useSelector` extracts a slice of the Redux store. `RootState` is the full store type, and `state.search` selects the search slice. See `frontend/src/store/store.ts` for type definitions.

### Q: Why use `type="stepAfter"` in a Recharts Line component?
- A) It makes the line animate on hover
- B) It creates a step function (flat then vertical) like Kaplan-Meier curves ✓
- C) It adds data points after each step
- D) It delays rendering until data loads
**Explanation**: `stepAfter` creates a step function where the line stays flat until the next data point, then drops vertically. This is standard for survival curves. See `frontend/src/components/KaplanMeierPlot.tsx`.

### Q: What's wrong with this React code?
```typescript
const [data, setData] = useState([]);
useEffect(() => {
  fetchData().then(setData);
}, []);
```
- A) Missing cleanup function for the effect
- B) Missing error handling ✓
- C) Should use `async/await` inside useEffect
- D) The dependency array should include `fetchData`
**Explanation**: The `.then()` call has no `.catch()`, so errors are silently swallowed. Always handle errors in async operations. The dep array is fine since `fetchData` is likely stable.

### Q: What does `createAsyncThunk` return when the API call fails?
- A) `undefined`
- B) A rejected action with error payload ✓
- C) It throws an unhandled exception
- D) A fulfilled action with null payload
**Explanation**: When the callback throws or calls `rejectWithValue()`, the thunk dispatches a rejected action. Handle it in `extraReducers` with `.addCase(thunk.rejected, ...)`. See `frontend/src/store/authSlice.ts`.

## Redux Toolkit

### Q: Why can you "mutate" state directly inside Redux Toolkit reducers?
- A) Redux Toolkit doesn't use immutability
- B) Redux Toolkit uses Immer internally to create immutable updates ✓
- C) JavaScript objects are always passed by value
- D) React re-renders regardless of state changes
**Explanation**: Redux Toolkit wraps reducers with Immer, which tracks mutations to a draft state and produces a new immutable state. `state.query = action.payload` is actually safe. See `frontend/src/store/searchSlice.ts`.

### Q: What is the purpose of `extraReducers` in a slice?
- A) To add reducers from other slices
- B) To handle actions from async thunks (pending/fulfilled/rejected) ✓
- C) To add middleware to the store
- D) To create additional action creators
**Explanation**: `extraReducers` responds to actions defined outside the slice, especially async thunk lifecycle actions. See the auth slice for a full example.

### Q: What does `rejectWithValue(message)` do inside a thunk?
- A) Throws a JavaScript error
- B) Dispatches a rejected action with the message as payload ✓
- C) Logs the error and continues
- D) Retries the async operation
**Explanation**: `rejectWithValue` creates a rejected action with a custom payload instead of the raw error. This allows cleaner error handling in the reducer.

## Survival Analysis

### Q: What does a hazard ratio of 1.5 mean?
- A) 50% of patients survived
- B) Patients have 50% higher risk of the event ✓
- C) Median survival is 1.5 months
- D) The p-value is 0.15
**Explanation**: HR > 1 means increased risk. HR = 1.5 means 50% higher hazard rate compared to the reference group. HR < 1 is protective.

### Q: Why do we use `np.exp(cph.params_['expression'])` to get the hazard ratio?
- A) Cox regression returns log-transformed coefficients ✓
- B) The exponential makes the value positive
- C) It converts from months to years
- D) It normalizes the coefficient
**Explanation**: Cox PH regression estimates log-hazard ratios (coefficients). Exponentiating converts them to hazard ratios: `HR = exp(beta)`. See `backend/app/services/survival_analysis_service.py`.

### Q: What is censoring in survival analysis?
- A) Removing outlier data points
- B) When the event of interest was not observed for a subject ✓
- C) Hiding patient identifying information
- D) Filtering genes with low expression
**Explanation**: Censoring occurs when a patient is lost to follow-up or the study ends before the event. They contribute partial information (survived at least X time). Marked as `event=0`.

### Q: What is the minimum recommended number of events for Cox regression?
- A) 3
- B) 5
- C) 10 ✓
- D) 50
**Explanation**: At least 10 events are recommended for reliable Cox regression. Fewer events lead to convergence issues and unreliable hazard ratio estimates. See `backend/app/services/survival_analysis_service.py`.

### Q: What does the log-rank test compare?
- A) Mean expression levels between groups
- B) Survival distributions between two or more groups ✓
- C) Hazard ratios across datasets
- D) Gene expression variance
**Explanation**: The log-rank test is a non-parametric test comparing survival curves between groups. A significant p-value means the groups have different survival experiences. See `lifelines.statistics.logrank_test`.

## SQLAlchemy

### Q: Why use `async_sessionmaker` instead of regular `sessionmaker`?
- A) It's faster for all operations
- B) It creates sessions compatible with async/await database operations ✓
- C) It automatically handles transactions
- D) It provides connection pooling
**Explanation**: `async_sessionmaker` creates `AsyncSession` instances that work with `await` for non-blocking database I/O using asyncpg. See `backend/app/config/database.py`.

### Q: What does `expire_on_commit=False` do in session configuration?
- A) Sessions never expire
- B) Attributes remain accessible after commit without re-querying ✓
- C) Commits are disabled
- D) Objects are cached forever
**Explanation**: By default, SQLAlchemy expires all attributes after commit, requiring a new query to access them. `expire_on_commit=False` keeps the data available, which is useful in async contexts.

### Q: What is the purpose of `cascade="all, delete-orphan"` in a relationship?
- A) It prevents deletion of parent records
- B) Deleting a parent automatically deletes its children ✓
- C) It creates a many-to-many relationship
- D) It adds an index on the foreign key
**Explanation**: Cascade delete means when a User is deleted, all their Conversations are automatically deleted too. `delete-orphan` removes children that are disassociated from their parent.

## pandas

### Q: What's more efficient for applying a function to a DataFrame column?
- A) A for loop iterating over rows
- B) `df.apply(func, axis=1)`
- C) Vectorized operations with numpy/pandas ✓
- D) List comprehension
**Explanation**: Vectorized operations (e.g., `df['col'] > threshold`) are orders of magnitude faster than loops or apply. pandas is built on numpy arrays optimized for bulk operations.

### Q: What does `pd.DataFrame.merge()` default join type?
- A) Left join
- B) Right join
- C) Inner join ✓
- D) Outer join
**Explanation**: The default `how='inner'` keeps only rows with matching keys in both DataFrames. Use `how='left'` to keep all rows from the left DataFrame. This matters when joining expression and clinical data.

## LangChain

### Q: What is the difference between `ChatMistralAI` and `ChatAnthropic` in this project?
- A) They use different prompt formats
- B) They are different LLM provider wrappers following the same ChatModel interface ✓
- C) One is for chat, the other for completion
- D) They require different API keys but are otherwise identical
**Explanation**: Both implement the LangChain `BaseChatModel` interface, making them interchangeable. The project supports both Mistral and Claude models via `langchain-mistralai` and `langchain-anthropic`.

### Q: What does `streaming=True` do when initializing a ChatModel?
- A) It saves the conversation to disk
- B) It returns tokens as they are generated instead of waiting for completion ✓
- C) It enables multi-turn conversations
- D) It reduces API costs
**Explanation**: Streaming delivers tokens incrementally via callbacks, improving perceived latency for the user. The chat system uses this for real-time response delivery. See `backend/app/services/chat/langchain_service.py`.

## Auth

### Q: Why use Argon2 instead of bcrypt for password hashing?
- A) Argon2 is faster
- B) Argon2 is memory-hard, making GPU attacks more expensive ✓
- C) Argon2 is the only algorithm supported by Python
- D) bcrypt has been deprecated
**Explanation**: Argon2 won the Password Hashing Competition. It's memory-hard (requires significant RAM), making parallel GPU/ASIC attacks impractical. This project uses it via `pwdlib[argon2]`.

### Q: What should happen when a JWT token expires?
- A) Silently refresh it in the background
- B) Return a 401 Unauthorized response ✓
- C) Return a 403 Forbidden response
- D) Extend the token automatically
**Explanation**: Expired tokens should return 401, prompting the client to use a refresh token or re-authenticate. The Axios interceptor catches 401s and handles logout. See `frontend/src/services/api.ts`.

## Async Python

### Q: What's wrong with using `time.sleep(5)` in an async function?
- A) It doesn't work in Python 3.13
- B) It blocks the entire event loop, preventing other coroutines from running ✓
- C) It sleeps for 5 milliseconds instead of seconds
- D) Nothing, it works correctly in async functions
**Explanation**: `time.sleep()` is synchronous and blocks the event loop thread. Use `await asyncio.sleep(5)` instead. Similarly, use `httpx.AsyncClient` instead of `requests`.

### Q: What does `asyncio.gather(*tasks, return_exceptions=True)` do?
- A) Ignores all exceptions
- B) Runs tasks concurrently and returns exceptions as values instead of raising ✓
- C) Retries failed tasks automatically
- D) Only returns results from successful tasks
**Explanation**: `return_exceptions=True` includes exception objects in the results list instead of propagating them. This lets you handle partial failures without losing successful results. See the orchestrator pattern.
