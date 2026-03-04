---
description: Review and improve implemented features - fix code quality, remove technical debt, consider better architectural approaches, and verify changes
user-invocable: true
argument-hint: "[F-id|frontend|backend|component-name]"
---

# Feature Cleanup and Architectural Review

Review implemented code for quality issues, technical debt, and better approaches.

## Parse Arguments

`$ARGUMENTS` determines scope:
- `F01`–`F15` → review files changed by that specific feature (read spec from `.claude/skills/implement-feature/references/F[id].md`)
- `frontend` → review all recently changed frontend files
- `backend` → review all recently changed backend files
- `[filename]` → review that specific file/component (e.g., `KaplanMeierPlot`, `orchestrator`)
- empty → ask the user for scope before proceeding

## Workflow

### Step 1: Identify Files

Run to see recently changed files:
```bash
git diff --name-only HEAD~5 HEAD
```

Filter by scope:
- For feature IDs: read the spec file to know which files were changed
- For `frontend`/`backend`: filter the git diff list by directory
- For named component: find the file with Glob

### Step 2: Read and Analyze Each File

Check all of the following:

**TypeScript / React quality**:
- `any` types that should be specific interfaces?
- Missing null checks before `.map()`, `.filter()`, object property access?
- `useEffect` with missing or incorrect dependency arrays?
- Missing `key` props on list items?
- State mutations (mutating Redux state outside a reducer)?
- Large components that mix logic and UI (consider splitting)?
- Prop drilling that should use Redux instead?
- Unused imports, unused variables?

**Python / FastAPI quality**:
- Bare `except:` or `except Exception` catching everything silently?
- Synchronous I/O inside an async function (e.g., `open()`, `requests.get()`)?
- Missing type hints on function parameters/returns?
- Tight coupling between layers (route logic in service, or service logic in routes)?
- LRU cache without bounds (`@lru_cache` without `maxsize`)?
- Missing `await` on coroutines?
- Pydantic models that could use validators?

**Performance**:
- SQLAlchemy: relationships loaded without `joinedload` causing N+1 queries?
- React: expensive derivations without `useMemo`?
- Missing database indexes for new FK or frequently-queried columns?
- Fetching full objects when only specific fields needed (`SELECT *` anti-pattern)?
- Large state updates re-rendering components that shouldn't re-render?

**Architecture** (check against `.claude/rules/backend.md` and `.claude/rules/frontend.md`):
- Does this code follow the service layer pattern (routes → services → clients)?
- Is there duplicated logic that already exists elsewhere?
- Is an abstraction being created for a one-time use case (premature abstraction)?
- Could this be simplified without losing functionality?
- Are there error states that should be handled but aren't?

**Better Approaches**:
- Is there a simpler way to achieve the same result?
- Are there existing utilities in `services/`, `store/`, or components that could be reused?
- Does the implementation have correctness edge cases (empty arrays, null values, race conditions)?

### Step 3: Categorize Issues

Group findings:
- **Critical**: bugs that could cause errors in production (null derefs, unhandled promises, type errors)
- **Warning**: code that works but will cause problems at scale or is hard to maintain
- **Suggestion**: style improvements, minor simplifications

### Step 4: Apply or Propose Fixes

**Auto-fix directly** (low risk):
- TypeScript type improvements (replacing `any`, adding null checks)
- Removing unused imports and variables
- Adding missing `key` props
- Adding obvious missing `await`

**Propose before applying** (ask for confirmation):
- Restructuring component logic (splitting, moving to Redux)
- Changing service layer boundaries
- Replacing an approach with a different pattern
- Any change affecting 3+ files

Show before/after for all proposed changes.

### Step 5: Verify

After applying any fixes:
```bash
# If frontend files changed:
cd frontend && npx tsc --noEmit && npm run build

# If backend files changed:
cd backend && uv run python -m py_compile $(find app -name "*.py" | head -20)

# If tests exist:
cd backend && uv run pytest
```

### Step 6: Output Summary

Provide:
1. Files reviewed
2. Issues found (critical / warnings / suggestions count)
3. Changes applied
4. Proposals pending your approval
5. Assessment: "Ready for next feature" or "Needs more work"

## Example Invocations

- `/cleanup` → ask for scope, then review
- `/cleanup F04` → review the CSV+PNG export implementation
- `/cleanup F05` → review the SSE progress implementation
- `/cleanup frontend` → review all recently changed frontend files
- `/cleanup backend` → review all recently changed backend services
- `/cleanup KaplanMeierPlot` → review that specific component
- `/cleanup orchestrator` → review the workflow orchestrator service
