# Skill Format Reference

Complete reference for `.claude/skills/<name>/SKILL.md`.

---

## Directory Structure

```
.claude/skills/<name>/
├── SKILL.md              ← required
└── references/           ← optional; for large content (>300 lines)
    ├── topic-a.md
    └── topic-b.md
```

Optional extras (rarely needed in this project):
```
└── scripts/              ← executable helpers bundled with the skill
└── assets/               ← templates, icons, fonts
```

---

## Three-Level Loading System

| Level | What loads | When |
|-------|------------|------|
| Metadata | `name` + `description` only | Always (every session) |
| Skill body | Full `SKILL.md` content | When skill is triggered |
| References | Files in `references/` | On demand — when Claude reads them |

This means: keep `SKILL.md` focused (under 500 lines). Large reference content belongs in `references/` with a clear pointer from the body: "For AWS-specific patterns, read `references/aws.md`."

---

## Frontmatter Fields

### Required

**`name`** — Skill identifier, must be kebab-case. Matches the directory name. Used for `/skill-name` invocation.
```yaml
name: api-development
```

**`description`** — The primary trigger mechanism. Claude reads this to decide whether to use the skill. Include:
- What the skill does (concrete, specific)
- When to use it (explicit contexts, user phrases, edge cases)
- Make it slightly "pushy" — Claude undertriggers by default. Err toward listing more triggering contexts than fewer.

```yaml
# Too vague — Claude will miss many valid uses:
description: FastAPI patterns for this project.

# Better — specific what + explicit when:
description: FastAPI backend development patterns for this project. Use when creating or modifying API endpoints, Pydantic models, service layer code, or async patterns.
```

---

### Optional: Parameterization

**`argument-hint`** — Shows a hint when the user invokes `/skill-name`. Use when the skill takes an argument (e.g., a feature ID, a module name).

```yaml
argument-hint: "<F-id>"
# Enables: /implement-feature F01
```

---

### Optional: Agent-Skill Fields

These fields turn a skill into an autonomous agent that Claude Code can spawn. Most skills don't need them.

**`tools`** — List of tools the agent can use. Omit for non-agent skills.
```yaml
tools: Read, Grep, Glob, Bash, Write, Edit, WebSearch
```

Available tools: `Read`, `Write`, `Edit`, `Grep`, `Glob`, `Bash`, `Agent`, `WebSearch`, `WebFetch`, `NotebookEdit`

**`model`** — LLM model for the agent. Omit for non-agent skills.
```yaml
model: sonnet   # for complex reasoning
model: haiku    # for simple/fast tasks (log checking, git ops)
```

**`skills`** — Dependent skills this agent loads. Avoids duplicating patterns.
```yaml
skills:
  - api-development
  - react-frontend
```

**`memory`** — Whether the agent maintains persistent memory across conversations.
```yaml
memory: project       # shared across all conversations for this project
memory: conversation  # only within the current conversation
```

**`maxTurns`** — Maximum agent turns before stopping. Prevents runaway cost.
```yaml
maxTurns: 30   # sonnet agents
maxTurns: 20   # haiku agents
```

---

## Writing Patterns

### Output format definition

Use explicit templates when the output structure matters:
```markdown
## Report structure

Always use this exact format:
# [Dataset ID]
## Summary
## Genes Found
## Recommendations
```

### Examples

Include concrete input/output examples:
```markdown
## Commit message format

**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication

**Example 2:**
Input: Fixed the null pointer crash on gene lookup
Output: fix(genes): handle missing probe mapping gracefully
```

### References pattern

For large skills (approaching 500 lines) or domain-split content, use `references/`:
```markdown
For detailed implementation patterns:
- Backend patterns → `references/backend.md`
- Frontend patterns → `references/frontend.md`
```

For multi-variant skills (e.g., cloud providers, analysis types):
```
skill-name/
├── SKILL.md        ← workflow + selection logic
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

Claude reads only the relevant reference file based on context — no need to load all variants.

### Table of contents for large reference files

If a reference file exceeds ~300 lines, add a table of contents at the top so Claude can jump to the relevant section without reading everything.

---

## Skill vs. Agent vs. Command vs. Rule

| Type | When to use | Example |
|------|------------|---------|
| **Skill** | On-demand knowledge, triggered by context | `api-development`, `survival-analysis` |
| **Agent** | Autonomous task execution, multi-step work | `postgres-manager`, `code-reviewer` |
| **Command** | User-invokable workflows, `/command-name` | `backend`, `roadmap`, `git` |
| **Rule** | Always-active constraints, loaded every session | `critical.md`, `git.md` |

Skills load only when triggered. Rules load every session regardless. Use skills for content that's only relevant for specific tasks; use rules only for constraints that must always apply (e.g., "never use bare except").

---

## This Project's Skill Naming Conventions

- Use kebab-case: `geo-data`, `oauth2-jwt-auth`, `api-development`
- Domain-specific: name by what it knows, not what it does (`langchain-chat` not `chat-helper`)
- Match the directory name exactly to the `name` field in frontmatter
