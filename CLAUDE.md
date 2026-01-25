# Claude Code Project Instructions

> GEO Survival Analysis - Analyze gene expression survival associations from NCBI GEO datasets.

## Quick Reference

| Stack | Technologies |
|-------|--------------|
| Backend | Python 3.13+, FastAPI, lifelines, uv |
| Frontend | React 18, TypeScript, Redux Toolkit, Tailwind |

## Critical Rules

1. **No bare exceptions** - Catch specific exception types
2. **Use `uv run`** - Prefix all Python commands
3. **No standalone .md files** - Don't create docs
4. **Async first** - Use async/await for I/O

## Commands

```bash
# Backend
cd backend && uv run python -m uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

## Project Structure

```
.claude/
├── agents/      # Custom AI agents (code-reviewer, api-debugger, etc.)
├── commands/    # Slash commands (/presentation, /backend, /frontend)
├── rules/       # Modular project rules (auto-loaded)
└── skills/      # Domain knowledge (survival-analysis, geo-data, etc.)
```

## Domain Context

- **Kaplan-Meier**: Survival probability curves
- **Cox regression**: Hazard ratios (HR)
- **HR > 1**: Increased risk | **HR < 1**: Protective

## Environment

Required in `backend/.env`:
```
MISTRAL_KEY=your_key
EMAIL=your_email@example.com
```
