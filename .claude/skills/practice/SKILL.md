---
name: practice
description: Generate coding practice exercises for project technologies. Use when the user wants to practice or train on FastAPI, React, Redux, Recharts, Tailwind, SQLAlchemy, survival analysis, LangChain, pandas, or authentication.
disable-model-invocation: true
argument-hint: "<topic> [difficulty]"
---

# Coding Practice Exercise Generator

Generate hands-on coding exercises based on this project's tech stack. Exercises include starter code, tests, and acceptance criteria.

## Usage

```
/practice <topic> [difficulty]
```

**Topics**: `fastapi`, `react`, `redux`, `recharts`, `tailwind`, `sqlalchemy`, `survival`, `langchain`, `pandas`, `auth`
**Difficulty**: `beginner` (default), `intermediate`, `advanced`

## Workflow

### Step 1: Parse Arguments

Parse `$ARGUMENTS` to extract topic and difficulty. If no difficulty is specified, default to `beginner`. If no topic is specified, ask the user to choose one.

### Step 2: Load Exercise Templates

1. Read the exercise reference file: `references/<topic>.md` (relative to this skill)
2. Read the corresponding project skill for real patterns:
   - `fastapi` → `.claude/skills/api-development/SKILL.md`
   - `react` → `.claude/skills/react-frontend/SKILL.md`
   - `redux` → `.claude/skills/react-frontend/SKILL.md`
   - `recharts` → `.claude/skills/react-frontend/SKILL.md`
   - `sqlalchemy` → `.claude/skills/postgres-database/SKILL.md`
   - `survival` → `.claude/skills/survival-analysis/SKILL.md`
   - `langchain` → `.claude/skills/langchain-chat/SKILL.md`
   - `auth` → `.claude/skills/oauth2-jwt-auth/SKILL.md`
   - `pandas`, `tailwind` → use reference file only

### Step 3: Generate Exercise

Pick one exercise from the reference file matching the requested difficulty. Adapt it using real project patterns. Generate:

1. **Exercise description** — Present to the user with clear requirements
2. **Starter code file** — Write to `practice_exercises/`:
   - Python exercises: `practice_exercises/<topic>_exercise.py`
   - TypeScript exercises: `practice_exercises/<topic>_exercise.tsx`
   - Include TODO comments marking where the user should implement
   - Include all necessary imports
3. **Test file** — Write alongside the starter code:
   - Python: `practice_exercises/test_<topic>_exercise.py`
   - TypeScript: `practice_exercises/<topic>_exercise.test.tsx`
   - 3-5 test cases covering the acceptance criteria
   - Tests should FAIL initially (user needs to implement the solution)

### Step 4: Present Exercise

Display to the user:
- Exercise title and difficulty badge
- Task description with clear requirements
- File paths for starter code and tests
- How to run the tests:
  - Python: `cd practice_exercises && uv run pytest test_<topic>_exercise.py -v`
  - TypeScript: `cd practice_exercises && npx vitest <topic>_exercise.test.tsx`
- Acceptance criteria checklist
- Hint: "Ask me for hints if you get stuck, or tell me when you're done for a code review"

### Step 5: Validate Solution (when user says they're done)

1. Run the test file
2. Read the user's implementation
3. Provide feedback on:
   - Test results (pass/fail)
   - Code quality and adherence to project patterns
   - Performance considerations
   - Suggestions for improvement
4. Offer to increase difficulty or try a different topic

## Exercise File Conventions

- Always create `practice_exercises/` directory if it doesn't exist
- Include `# Practice Exercise: <title>` header in starter files
- Include `# Difficulty: <level>` in starter files
- Python files use project conventions: type hints, async where appropriate, specific exceptions
- TypeScript files use strict mode, proper interfaces, React.FC pattern

## Reference Files

For exercise templates by topic, see:
- [FastAPI exercises](references/fastapi.md)
- [React/TypeScript exercises](references/react-typescript.md)
- [Redux exercises](references/redux.md)
- [Recharts exercises](references/recharts.md)
- [Tailwind exercises](references/tailwind.md)
- [SQLAlchemy exercises](references/sqlalchemy.md)
- [Survival analysis exercises](references/survival-analysis.md)
- [pandas exercises](references/pandas.md)
- [LangChain exercises](references/langchain.md)
- [Auth exercises](references/auth.md)
