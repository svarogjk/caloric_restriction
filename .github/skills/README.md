# GitHub Copilot Skills

This directory contains Agent Skills for GitHub Copilot. Skills are automatically loaded when your prompt matches their description.

## Available Skills

| Skill | Description | Use When |
|-------|-------------|----------|
| [survival-analysis](./survival-analysis/SKILL.md) | Kaplan-Meier, Cox regression, hazard ratios | Working with survival analysis code |
| [geo-data](./geo-data/SKILL.md) | GEO database, expression data, probe mapping | Fetching or parsing GEO data |
| [geo-platform-streaming](./geo-platform-streaming/SKILL.md) | Stream large GPL SOFT files (~GB) to extract probe→gene mappings | Downloading platforms >200MB without OOM/timeout |
| [api-development](./api-development/SKILL.md) | FastAPI, Pydantic, async services | Creating or modifying API endpoints |
| [react-frontend](./react-frontend/SKILL.md) | React, Redux, Tailwind, Recharts | Building frontend components |

## How Skills Work

1. You write a prompt in Copilot
2. Copilot matches your prompt against skill descriptions
3. Relevant skill instructions are loaded into context
4. Copilot uses the skill knowledge to generate better responses

## Example Prompts

**Survival Analysis:**
- "Add a function to compute median survival time"
- "Fix the Cox regression convergence error"

**GEO Data:**
- "Download expression matrix for GSE12345"
- "Map probe IDs to gene symbols"

**GEO Platform Streaming:**
- "Download GPL5175 platform mapping without downloading the full 4GB file"
- "Stream-parse a large GPL SOFT file to get probe gene mappings"
- "Add platform mapping for GPL16686 efficiently"

**API Development:**
- "Create a new endpoint for gene lookup"
- "Add validation to the search request"

**React Frontend:**
- "Create a component to display survival curves"
- "Add loading state to the search results"

## Creating New Skills

1. Create a folder under `.github/skills/`
2. Add a `SKILL.md` file with frontmatter:

```markdown
---
name: skill-name
description: When to use this skill
---

# Skill Instructions

Your detailed instructions here...
```

## References

- [GitHub Docs: About Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)
- [VS Code: Use Agent Skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills)
