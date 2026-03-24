# Skill Examples from This Project

Three representative skills showing different patterns. Use these as templates.

---

## Pattern 1: Simple Inline Skill (no references/)

**[api-development/SKILL.md](.claude/skills/api-development/SKILL.md)**

Best for: domain knowledge that fits in ~135 lines with no subdomains.

```yaml
---
name: api-development
description: FastAPI backend development patterns for this project. Use when creating or modifying API endpoints, Pydantic models, service layer code, or async patterns.
---
```

**Structure:**
- No `references/` directory — all content inline
- Organized into sections: Project Structure, Route Pattern, Pydantic Models, Error Handling, Service Layer, Async Patterns, Dependency Injection, Testing
- Each section is a short code block — concrete, copy-paste ready
- ~135 lines total

**What makes this work:** Short, dense, zero abstraction. Every line is a real pattern from the codebase. No prose explaining what FastAPI is — the skill assumes the reader can code.

---

## Pattern 2: Parameterized Skill with References (argument-hint)

**[implement-feature/SKILL.md](.claude/skills/implement-feature/SKILL.md)**

Best for: skills that operate on one item from a known set (feature IDs, module names, dataset types).

```yaml
---
name: implement-feature
description: Full implementation specs for product roadmap features F01-F15. Auto-invoked when implementing roadmap features. Use as /implement-feature F01 to get the full spec and implement a specific feature.
argument-hint: "<F-id>"
---
```

**Structure:**
```
implement-feature/
├── SKILL.md          ← index + usage instructions (~73 lines)
└── references/
    ├── F01.md        ← self-contained spec for feature F01
    ├── F02.md
    └── ... (F01-F15)
```

**SKILL.md body:**
- Usage instructions: how to invoke (`/implement-feature F01`)
- Session start template: what to say when invoked
- Feature index table: ID, Name, Size, Dependencies
- Links to each `references/F[id].md`

**What makes this work:** The SKILL.md is just an index and instructions. The real content is in `references/` — Claude reads only the one relevant spec file for the requested feature, not all 15. This is the progressive disclosure pattern: metadata → index → one spec.

**Invocation:**
```
/implement-feature F01
# or
"let's implement the gene search feature"   ← auto-triggers via description
```

---

## Pattern 3: Skill with Domain-Split References (backend/frontend)

**[oauth2-jwt-auth/SKILL.md](.claude/skills/oauth2-jwt-auth/SKILL.md)**

Best for: full-stack features where backend and frontend patterns would bloat a single file.

```yaml
---
name: oauth2-jwt-auth
description: Full-stack OAuth2 JWT authentication patterns for FastAPI backend and React frontend. Use when implementing user registration, login, token management, route protection, or auth components.
---
```

**Structure:**
```
oauth2-jwt-auth/
├── SKILL.md              ← overview + key patterns (~120 lines)
└── references/
    ├── backend.md        ← detailed backend implementation code
    └── frontend.md       ← detailed frontend implementation code
```

**SKILL.md body:**
- Project structure (where files live)
- Key patterns for both stacks: password hashing, JWT creation, route protection, token management
- Error response table
- Testing examples (curl commands)
- Footer: "For detailed implementation code, see references/backend.md and references/frontend.md"

**What makes this work:** The SKILL.md gives you enough to understand the pattern and start coding. The `references/` files have the full boilerplate to copy when you need it. Claude reads references on demand — when it needs the full SQLAlchemy model or the Axios interceptor code.

---

## Anti-Patterns to Avoid

**Too vague in description:**
```yaml
# Bad — will undertrigger:
description: Patterns for database work.

# Good — specific contexts listed:
description: PostgreSQL database management patterns for this project. Use when working with database schema, Alembic migrations, SQLAlchemy async configuration, Docker setup, or query optimization.
```

**Instructions without why:**
```markdown
# Bad — model applies this rigidly even when wrong:
NEVER use asyncio.run() inside an async function.

# Good — model understands and applies intelligently:
Don't use asyncio.run() inside an async function — it creates a nested event loop
which raises a RuntimeError in Python 3.10+. Use await directly instead.
```

**One giant file instead of references/:**
```
# Bad — 600-line SKILL.md with all content inline

# Good — 120-line SKILL.md + references/backend.md + references/frontend.md
```

**Missing `argument-hint` for parameterized skills:**
```yaml
# Bad — user doesn't know what argument to pass:
name: implement-feature
description: Implement a feature.

# Good — hint tells user the expected argument format:
name: implement-feature
argument-hint: "<F-id>"
```
