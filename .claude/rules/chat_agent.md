# Chat Agent Rules

## Differentiation Mandate

Every AI chat response MUST be grounded in real GEO data. A response that could be produced by ChatGPT.com — without calling any tool or citing any dataset — has zero product value and undermines the app's core moat.

## Required Behaviors

- Call at least one tool on every substantive user question
- Include GSE accession IDs in any response about available datasets (e.g. GSE12345)
- Never suggest organism, cancer type, or gene filter improvements that are ALREADY set in `user_settings` — the dynamic system prompt block tells the agent exactly what is configured
- The `search_geo_datasets` and `get_gene_info` tools resolve organism from `ctx.deps.user_settings` — never hardcode "Homo sapiens" in tool defaults

## When No Suitable Tool Exists

If the agent cannot answer a substantive domain question using existing tools (e.g. "show me the KM curve for TP53 in GSE12345", "run differential expression", "compare two analyses"), the correct response is:

1. Acknowledge the gap explicitly: "I don't currently have a tool for X"
2. Explain what data/capability would be needed
3. Ask the user: "Would you like me to propose a new tool for this?"

If the user approves, open a discussion with the developer (via the chat UI or a GitHub issue):
- Describe what the tool should do (inputs, outputs, side-effects)
- Identify which backend service/endpoint it would call
- Confirm it follows the tool pattern in `agent_tools.py`

**Never hallucinate a capability.** If a tool doesn't exist, say so and propose building it rather than fabricating a result.

## Settings Propagation Chain

```
Redux (organism, cancerGenesOnly, datasetCount, rankingMultiplier, geneFilterInput)
  → sendMessage thunk builds UserSettings
  → sendMessageStream POST body: { user_settings: {...} }
  → SendMessageRequest.user_settings (chat_routes.py)
  → chat_service.stream_message(user_settings=..., user_id=...)
  → AgentDeps(user_settings=...) per-request
  → pydantic_ai_service: dynamic @agent.system_prompt reads ctx.deps.user_settings
  → tool organism defaults read ctx.deps.user_settings
```

## Domain Score

Each AI message gets a **Domain Score (DS)** badge (0–100). Computed zero-cost in `pydantic_ai_service._compute_domain_score()`:

| Signal | Points |
|---|---|
| Each tool called | +20, max 40 |
| Each `GSE\d+` citation | +15, max 30 |
| HR / p-value / n= samples in text | +15 |
| User organism or candidate gene in text | +15 |

**Targets:** DS ≥ 70 for domain queries (green badge). DS 0–20 for purely conceptual questions ("what is a hazard ratio?") is acceptable — the score is honest, not inflated.

Logged via: `logger.info("chat_metrics conversation_id=%s tools=%s gse_citations=%d domain_score=%d", ...)` in `pydantic_ai_service.py`.

## Measurement KPIs

Query logs with: `grep chat_metrics geo_logs/app.log`

- **Tool invocation rate**: ≥ 70% of assistant turns must call ≥ 1 tool
- **GSE citation rate**: ≥ 50% of tool-using turns must cite ≥ 1 GSE ID
- **DS ≥ 70 rate**: target ≥ 60% of substantive domain questions

## Never Do

- Suggest settings already configured by the user
- Return tool errors silently (always log with `logger.warning`)
- Hardcode organism in tool defaults — always resolve from `ctx.deps.user_settings`
- Cache agents after changing the system prompt registration — `set_deps()` clears `self._agents`
- Store user PII or API keys in tool return values or logs
- Hallucinate a capability that no tool supports — acknowledge the gap and propose a new tool
