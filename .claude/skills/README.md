# Claude Code Skills

This directory contains skills for Claude Code. Skills provide specialized knowledge and code patterns for specific domains in this project.

## Available Skills

| Skill | Description | Use When |
|-------|-------------|----------|
| [survival-analysis](survival-analysis.md) | Kaplan-Meier, Cox regression, hazard ratios | Working with survival analysis code |
| [geo-data](geo-data.md) | GEO database, expression data, probe mapping | Fetching or parsing GEO data |
| [api-development](api-development.md) | FastAPI, Pydantic, async services | Creating or modifying API endpoints |
| [react-frontend](react-frontend.md) | React, Redux, Tailwind, Recharts | Building frontend components |

## How to Use Skills

Reference these skills in your prompts when working on related tasks. Claude Code will use the skill knowledge to provide better context-aware assistance.

### Example Prompts

**Survival Analysis:**
- "Add a function to compute median survival time"
- "Fix the Cox regression convergence error"

**GEO Data:**
- "Download expression matrix for GSE12345"
- "Map probe IDs to gene symbols"

**API Development:**
- "Create a new endpoint for gene lookup"
- "Add validation to the search request"

**React Frontend:**
- "Create a component to display survival curves"
- "Add loading state to the search results"

## Skill Structure

Each skill file contains:
- **Domain Knowledge**: Key concepts and terminology
- **Code Patterns**: Reusable code templates following project conventions
- **Project Integration**: How to integrate with existing services
- **Common Issues**: Troubleshooting guide for frequent problems

## Related Files

- [CLAUDE.md](../../CLAUDE.md) - Main project instructions for Claude Code
- [.github/copilot-instructions.md](../../.github/copilot-instructions.md) - General AI assistant guidelines
- [.github/skills/](../../.github/skills/) - GitHub Copilot skills (similar content)
