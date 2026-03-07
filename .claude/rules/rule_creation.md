---
paths:
  - ".claude/rules/**/*"
  - ".claude/CLAUDE.md"
---
 
# Rule Creation Standards
 
Rules must pass the **pruning test** on every line: *"Would removing this cause Claude to make mistakes?"* If not, cut it.
 
---
 
## Size Limits
 
| Type | Target | Max |
|------|--------|-----|
| Global rule (no `paths:`) | < 3 KB | 5 KB |
| Path-scoped rule | < 10 KB | 15 KB |
| `CLAUDE.md` | < 100 lines | 200 lines |
| Total global rules | < 15 KB | — |
 
---
 
## Path Scoping (Required Unless Justified)
 
Rules without `paths:` frontmatter load on **every** session. Only global rule is justified: `critical.md`. All others — including directory indexes like `README.md` — must be path-scoped.
 
All other rules must declare paths:
 
```yaml
---
paths:
  - "backend/api/feature.py"
  - "frontend/src/pages/Feature*"
---
```
 
---
 
## Include
 
- Project-specific patterns that differ from defaults
- Non-obvious behaviors that caused real bugs
- Exact function names, file paths, argument order Claude can't infer from code
- Patterns that must replicate Dash behavior exactly
 
## Exclude
 
- Anything Claude can determine by reading the code
- Standard Python/TypeScript/React conventions
- Step-by-step how-to instructions → use a **skill** instead
- Completed implementation history → **archive** instead
- References to files that no longer exist
- Self-evident practices ("write clean code", "add error handling")
 
---
 
## Rules vs Skills
 
| Rule (`.claude/rules/`) | Skill (`.claude/skills/`) |
|------------------------|--------------------------|
| "Always X" / "Never Y" constraints | Step-by-step how-to workflows |
| Gotcha from a real bug | Code templates |
| Must-match-Dash pattern | Multi-step migration guide |
 
---
 
## Archive Policy
 
Prefix with `_` when a migration plan is complete or a status doc is stale (> 2 months). The prefix prevents auto-loading while keeping history accessible. Do not delete.
 
---
 
## Checklist (Before Saving)
 
- [ ] Every line passes the pruning test
- [ ] Has `paths:` frontmatter (or explicit global justification written here)
- [ ] Under size limits
- [ ] No dead file references
- [ ] No completed-work history (archive instead)
- [ ] How-to instructions moved to a skill