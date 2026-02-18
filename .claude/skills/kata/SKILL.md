---
name: kata
description: Quick code kata exercises (5-15 min) for practicing project technologies in TDD style
disable-model-invocation: true
argument-hint: "[topic]"
---

# Code Kata - TDD Style

Quick, focused exercises where you write code to make failing tests pass. Each kata targets a single concept and takes 5-15 minutes.

## Usage

```
/kata [topic]
```

**Topics** (optional): `fastapi`, `react`, `redux`, `recharts`, `tailwind`, `sqlalchemy`, `survival`, `langchain`, `pandas`, `auth`, `pydantic`, `async`

If no topic is specified, pick one randomly from the list above.

## Workflow

### Step 1: Select Kata

Parse `$ARGUMENTS` for a topic. If none given, randomly choose from the topic list. Select a kata from the templates below matching the topic.

### Step 2: Create Exercise Files

Create `practice_exercises/kata/` directory if it doesn't exist.

1. **Test file first** (TDD style):
   - Python: `practice_exercises/kata/test_kata_<topic>_<short_name>.py`
   - TypeScript: `practice_exercises/kata/kata_<topic>_<short_name>.test.tsx`
   - Include 3-5 focused test cases
   - Tests must FAIL initially (import from implementation file)

2. **Empty implementation file**:
   - Python: `practice_exercises/kata/kata_<topic>_<short_name>.py`
   - TypeScript: `practice_exercises/kata/kata_<topic>_<short_name>.tsx`
   - Include only the function/class signatures with `pass` or empty returns
   - Include docstring/comments explaining expected behavior

### Step 3: Present Kata

Display:
- Kata title and estimated time (5-15 min)
- Topic and concept being practiced
- File paths for test and implementation
- Run command: `cd practice_exercises/kata && uv run pytest test_kata_<name>.py -v`
- Rule: "Make all tests pass without modifying the test file"

### Step 4: Validate (when user is done)

1. Run the tests
2. Read the implementation
3. Give brief feedback: correctness, style, edge cases
4. Suggest a follow-up kata or `/practice` exercise for deeper learning

## Kata Templates

### FastAPI
- **Route Handler**: Write an async endpoint that accepts a Pydantic model, validates input, returns structured response
- **Error Mapper**: Write a function that maps service exceptions to proper HTTPException status codes

### React
- **Props Transformer**: Write a function that transforms API response data into component props format
- **Custom Hook**: Write a `useDebounce` hook that delays value updates

### Redux
- **Slice Actions**: Write reducers for a loading/success/error state machine
- **Selector**: Write memoized selectors that derive computed state from the store

### Pydantic
- **Model Validation**: Write a Pydantic model with custom validators for scientific data (positive numbers, valid ranges)
- **Nested Models**: Write nested Pydantic models matching a complex API response

### Async
- **Semaphore Pool**: Write an async function that fetches multiple URLs with concurrency limit
- **Retry Logic**: Write an async retry decorator with exponential backoff

### pandas
- **Data Cleaning**: Write a function to clean clinical data (parse dates, handle missing values, normalize text)
- **Expression Matrix**: Write a function to filter a gene expression matrix by variance threshold

### Survival Analysis
- **Dichotomize**: Write a function to split patients into high/low expression groups by median
- **Result Formatter**: Write a function to format Cox regression results into a structured output

### SQLAlchemy
- **Query Builder**: Write an async function to query with filters, pagination, and sorting
- **Soft Delete**: Write a mixin class that adds soft delete behavior to any model

### Auth
- **Token Claims**: Write a function to create and decode JWT tokens with custom claims
- **Password Policy**: Write a password strength validator (length, complexity, common passwords)

### LangChain
- **Prompt Builder**: Write a function that constructs a ChatPromptTemplate from dynamic context
- **Output Parser**: Write a Pydantic model and parser for structured LLM output

### Recharts
- **Data Transform**: Write a function to transform raw survival data into Recharts-compatible format
- **Color Mapper**: Write a function that assigns colors based on statistical significance thresholds

### Tailwind
- **Class Builder**: Write a function that generates Tailwind class strings based on component variant props
- **Responsive Config**: Write a utility that maps breakpoint-aware props to Tailwind responsive classes
