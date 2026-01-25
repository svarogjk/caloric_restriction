# Claude Code Rules

This directory contains modular project rules that are automatically loaded by Claude Code.

## Available Rules

| Rule | Purpose |
|------|---------|
| [critical.md](critical.md) | Absolute requirements that must never be violated |
| [backend.md](backend.md) | Python/FastAPI backend conventions |
| [frontend.md](frontend.md) | React/TypeScript frontend conventions |
| [survival-analysis.md](survival-analysis.md) | Survival analysis domain rules |
| [geo-data.md](geo-data.md) | GEO database handling rules |

## How Rules Work

All `.md` files in this directory are automatically discovered and loaded as project memory. Rules are applied based on context - Claude Code uses relevant rules when working on matching files or domains.

## Rule Priority

1. Critical rules always apply
2. Backend rules apply when working in `backend/`
3. Frontend rules apply when working in `frontend/`
4. Domain rules apply when the task matches the domain

## Related Files

- [CLAUDE.md](../../CLAUDE.md) - Quick reference and project overview
- [.claude/skills/](../skills/) - Detailed domain knowledge and code patterns
- [.claude/agents/](../agents/) - Specialized AI agents for specific tasks
