---
name: implement-feature
description: Full implementation specs for product roadmap features F01-F15. Auto-invoked when implementing roadmap features. Use as /implement-feature F01 to get the full spec and implement a specific feature.
argument-hint: "<F-id>"
---

# Feature Implementation Guide

This skill provides self-contained implementation specs for each product roadmap feature. Each spec includes the problem, files to read first, implementation approach, verification commands, and commit message.

## Usage

```
/implement-feature F01
```

Or describe the feature: "let's implement the gene search feature" — this skill auto-invokes.

## Before Starting Any Feature

1. Read the feature spec: `references/F[id].md`
2. Read ALL files listed in "Files to Read First" in the spec
3. Implement the changes exactly as described
4. Run the "Verification Commands" from the spec — all must pass
5. Commit with the suggested message format
6. Mark feature as done in `/roadmap` (change `- [ ]` to `- [x]`)

## Session Start Template

When a user invokes `/implement-feature F01`, say:

> "I'll implement **F01: [name]** from the roadmap. Let me read the spec and relevant files first."

Then read `references/F[id].md` and all "Files to Read First" before writing any code.

## Feature Index

| ID | Name | Size | Depends On |
|---|---|---|---|
| F01 | Remove mock KM data | S | — |
| F02 | Gene search + filter + pagination | S | — |
| F03 | CI bands on KM curves | S | — |
| F04 | CSV + PNG export | S | — |
| F05 | Analysis progress SSE | M | — |
| F06 | Enable chat streaming | M | — |
| F07 | Persist analysis results to database | M | — |
| F08 | Forest plot tab | M | — |
| F09 | Shareable result URLs | M | F07 |
| F10 | Gene batch input mode | M | — |
| F11 | Pathway/GO enrichment | M | — |
| F12 | Analysis history dashboard | M | F07 |
| F13 | Multivariate Cox regression | L | — |
| F14 | Analysis comparison mode | L | F07, F12 |
| F15 | Publication export package | L | F07 |

## Spec Files

- [F01 — Remove mock KM data](references/F01.md)
- [F02 — Gene search + pagination](references/F02.md)
- [F03 — CI bands on KM curves](references/F03.md)
- [F04 — CSV + PNG export](references/F04.md)
- [F05 — Analysis progress SSE](references/F05.md)
- [F06 — Enable chat streaming](references/F06.md)
- [F07 — Persist results to database](references/F07.md)
- [F08 — Forest plot tab](references/F08.md)
- [F09 — Shareable result URLs](references/F09.md)
- [F10 — Gene batch input mode](references/F10.md)
- [F11 — Pathway/GO enrichment](references/F11.md)
- [F12 — Analysis history dashboard](references/F12.md)
- [F13 — Multivariate Cox regression](references/F13.md)
- [F14 — Analysis comparison mode](references/F14.md)
- [F15 — Publication export package](references/F15.md)
