---
name: explain-pattern
description: Explains architectural patterns used in this project with real code examples. Use when the user asks how something works, wants to understand a pattern, or asks about project architecture.
argument-hint: "<pattern-name>"
---

# Project Pattern Explainer

Explains architectural patterns from this project using real code examples. Helps developers understand why patterns were chosen and how to use them.

## Usage

```
/explain-pattern <pattern>
```

Can also be auto-invoked when you ask questions like:
- "How does the orchestrator pattern work?"
- "How is authentication implemented?"
- "What pattern does the service layer follow?"

## Workflow

### Step 1: Identify Pattern

Parse `$ARGUMENTS` or infer from conversation context. Match to one of the patterns in [references/patterns-catalog.md](references/patterns-catalog.md).

If the pattern is unclear, ask the user to choose from the available patterns.

### Step 2: Read Source Code

Read the actual source files listed in the patterns catalog for the matched pattern. These are real files in the project, not templates.

### Step 3: Explain the Pattern

Structure the explanation as:

1. **What it is**: One-paragraph overview of the pattern
2. **Why we use it**: The problem it solves in this project specifically
3. **How it works**: Step-by-step walkthrough using real code from the project
   - Show relevant code snippets from actual project files
   - Annotate key lines with explanations
   - Show the data flow through the pattern
4. **Key decisions**: Design choices made and alternatives considered
5. **Common variations**: How this pattern might be adapted for new features
6. **Gotchas**: Common mistakes when working with this pattern

### Step 4: Suggest Practice

Recommend related exercises:
- "Try `/practice <topic> intermediate` to build something using this pattern"
- "Try `/kata <topic>` for a quick exercise on a specific concept"
- Point to specific exercises that reinforce the pattern

## Pattern Recognition

Map user queries to patterns:

| User says | Pattern |
|-----------|---------|
| "orchestrator", "workflow", "coordinate" | Orchestrator Pattern |
| "service layer", "routes", "architecture" | Service Layer |
| "async", "await", "concurrent" | Async Patterns |
| "redux", "state", "slice", "thunk" | Redux State Management |
| "chart", "plot", "visualization" | Recharts Data Flow |
| "auth", "jwt", "token", "login" | JWT Authentication Flow |
| "llm", "agent", "ai", "detection" | LLM Agent with Fallback |
| "pydantic", "model", "validation" | Pydantic Model Pattern |
| "dependency", "inject", "depends" | FastAPI Dependency Injection |
| "database", "session", "query" | SQLAlchemy Async Sessions |
| "interceptor", "axios", "api client" | Axios Interceptor Pattern |
| "survival", "kaplan", "cox" | Survival Analysis Pipeline |

## Patterns Catalog Reference

For the complete catalog of patterns with source file locations, see [references/patterns-catalog.md](references/patterns-catalog.md).
