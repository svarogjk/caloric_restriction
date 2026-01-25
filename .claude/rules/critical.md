# Critical Rules

These rules must ALWAYS be followed without exception.

## Absolute Requirements

1. **No bare exceptions** - Always catch specific exception types or don't use try/except
   ```python
   # WRONG
   try:
       result = await fetch_data()
   except:
       pass

   # CORRECT
   try:
       result = await fetch_data()
   except httpx.HTTPError as e:
       logger.error(f"HTTP error: {e}")
       raise
   ```

2. **Use `uv run`** - Prefix ALL Python commands with `uv run`
   ```bash
   # WRONG
   python script.py
   pytest tests/

   # CORRECT
   uv run python script.py
   uv run pytest tests/
   ```

3. **No standalone .md files** - Never create explanation documents, READMEs, or documentation files unless explicitly requested

4. **Async first** - Use async/await for ALL I/O operations
   ```python
   # WRONG
   def fetch_dataset(gse_id: str):
       response = httpx.get(url)

   # CORRECT
   async def fetch_dataset(gse_id: str):
       async with httpx.AsyncClient() as client:
           response = await client.get(url)
   ```

## Environment Variables

Required in `backend/.env`:
```
MISTRAL_KEY=your_key
EMAIL=your_email@example.com
```

Never commit `.env` files. Never hardcode credentials.
