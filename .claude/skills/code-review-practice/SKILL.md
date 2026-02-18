---
name: code-review-practice
description: Practice code review by finding intentional bugs in backend (Python/FastAPI) or frontend (React/TypeScript) code
disable-model-invocation: true
argument-hint: "[backend|frontend] [difficulty]"
---

# Code Review Practice

Practice finding bugs in code. Claude generates a code snippet with intentional issues. You find them, then Claude reveals all bugs with explanations.

## Usage

```
/code-review-practice [backend|frontend] [difficulty]
```

**Domain**: `backend` (Python/FastAPI) or `frontend` (React/TypeScript). Default: `backend`.
**Difficulty**: `beginner`, `intermediate` (default), `advanced`

Difficulty controls bug count and subtlety:
- **Beginner**: 3-4 bugs, mostly obvious (missing imports, wrong types, syntax issues)
- **Intermediate**: 4-6 bugs, mix of obvious and subtle (logic errors, async issues, security)
- **Advanced**: 5-8 bugs, mostly subtle (race conditions, edge cases, performance, security)

## Workflow

### Step 1: Parse Arguments

Parse `$ARGUMENTS` for domain and difficulty. Defaults: `backend intermediate`.

### Step 2: Load Bug Patterns

Read the appropriate reference file:
- Backend: [references/bug-patterns-backend.md](references/bug-patterns-backend.md)
- Frontend: [references/bug-patterns-frontend.md](references/bug-patterns-frontend.md)

Also read the project's existing rules for conventions:
- Backend: `.claude/rules/backend.md`, `.claude/rules/critical.md`
- Frontend: `.claude/rules/frontend.md`

### Step 3: Generate Buggy Code

Create a realistic code snippet (50-100 lines) that:
- Looks like it belongs in this project (uses project patterns, imports, naming)
- Contains the target number of intentional bugs from different categories
- Has a plausible purpose (e.g., "a new service for analyzing gene sets" or "a dashboard component for dataset comparison")
- Is realistic enough that bugs aren't obvious from context alone

Write the buggy code to `practice_exercises/review/`:
- Backend: `practice_exercises/review/review_exercise.py`
- Frontend: `practice_exercises/review/review_exercise.tsx`

**Keep a private list** of all intentional bugs with:
- Line number
- Bug category (security, logic, performance, style)
- Description of the issue
- How to fix it

### Step 4: Present the Challenge

Display:
- Exercise title and difficulty
- Context: what the code is supposed to do
- File path to review
- Instructions: "Review this code and list all bugs you can find. Categorize each as: security, logic, performance, or style. Tell me when you're done."
- Bug count hint: "There are N intentional issues to find"

### Step 5: Score the Review (when user responds)

Compare the user's findings against the bug list:
1. **Found bugs**: Mark each correctly identified bug
2. **Missed bugs**: Reveal any bugs the user didn't find, with explanations
3. **False positives**: If the user flagged something that isn't a bug, explain why
4. **Score**: X/Y bugs found
5. **Category breakdown**: How many security vs logic vs performance vs style bugs were found

### Step 6: Debrief

- Explain each bug and its real-world impact
- Reference project rules that the bug violates
- Suggest areas to focus on based on missed bug categories
- Offer to try again with different difficulty or domain

## Bug Categories

### Security Bugs
- SQL injection, command injection
- Bare exceptions hiding errors
- Hardcoded secrets/credentials
- Missing authentication checks
- XSS vulnerabilities (frontend)
- Unsafe data deserialization

### Logic Bugs
- Off-by-one errors
- Wrong comparison operators
- Missing null/undefined checks
- Incorrect async/await usage
- Wrong data type assumptions
- Race conditions

### Performance Bugs
- N+1 queries
- Blocking I/O in async context
- Missing database indexes
- Unnecessary re-renders (frontend)
- Large bundle imports
- Missing memoization for expensive operations

### Style/Convention Bugs
- Violating project naming conventions
- Missing type annotations
- Using `any` type (TypeScript)
- Wrong import style
- Missing error handling patterns
- Not following project architecture (routes → services → clients)
