# Critical Rules

These rules must ALWAYS be followed without exception.

1. **No bare exceptions** - Catch specific exception types, never bare `except:` or `except Exception`
2. **Use `uv run`** - Prefix ALL Python commands: `uv run python`, `uv run pytest`, `uv run mypy`
3. **No standalone .md files** - Never create docs/READMEs unless explicitly requested
4. **Async first** - Use `async/await` for ALL I/O: `async with httpx.AsyncClient()`, not `httpx.get()`

## Environment

Required in `backend/.env`:
```
MISTRAL_KEY=your_key
EMAIL=your_email@example.com
```

Never commit `.env` files. Never hardcode credentials.
