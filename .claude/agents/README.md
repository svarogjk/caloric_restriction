# Claude Code Agents

This directory contains custom agents for Claude Code. Agents are specialized subcontexts that handle specific types of tasks with their own tools and permissions.

## Available Agents

| Agent | Description | Model | When to Use |
|-------|-------------|-------|-------------|
| [code-reviewer](code-reviewer.md) | Reviews code quality and conventions | sonnet | Before commits, during PR reviews |
| [api-debugger](api-debugger.md) | Debugs API issues and errors | sonnet | When API endpoints fail or return errors |
| [survival-analysis-planner](survival-analysis-planner.md) | Plans statistical analysis strategies | sonnet | Designing new survival analyses |
| [log-checker](log-checker.md) | Analyzes application logs | haiku | Investigating errors or performance issues |
| [frontend-helper](frontend-helper.md) | React/TypeScript development | sonnet | Creating components, Redux state |
| [git-manager](git-manager.md) | Git operations, commits, tags | haiku | Commits, pushes, pulls, tagging |

## How to Use Agents

Agents are automatically invoked by Claude Code when the task matches their description. You can also request specific agents explicitly:

```
Use the code-reviewer agent to review my recent changes
```

```
Have the api-debugger investigate why the search endpoint is failing
```

```
Ask the survival-analysis-planner to design a strategy for pan-cancer analysis
```

## Agent Structure

Each agent file uses YAML frontmatter with the following fields:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique identifier (lowercase, hyphens) |
| `description` | Yes | When to delegate to this agent |
| `tools` | No | Allowed tools (Read, Write, Edit, Bash, Grep, Glob) |
| `model` | No | Model to use: `sonnet`, `opus`, `haiku` |
| `skills` | No | Skills to preload into agent context |

## Comparison with GitHub Copilot Agents

This directory mirrors `.github/agents/` for GitHub Copilot. Key differences:

| Aspect | GitHub Copilot | Claude Code |
|--------|----------------|-------------|
| Location | `.github/agents/` | `.claude/agents/` |
| Format | `.agent.md` files | `.md` files |
| Tools | Copilot-specific | Read, Write, Edit, Bash, etc. |
| Models | N/A | sonnet, opus, haiku |
| Skills | N/A | Can preload domain skills |

## Creating New Agents

1. Create a new `.md` file in this directory
2. Add YAML frontmatter with `name`, `description`, and optionally `tools`, `model`, `skills`
3. Write the agent's instructions in markdown below the frontmatter
4. The agent will be available in your next Claude Code session

## Related Files

- [CLAUDE.md](../../CLAUDE.md) - Main project instructions
- [.claude/skills/](../skills/) - Domain-specific skills
- [.github/agents/](../../.github/agents/) - Equivalent GitHub Copilot agents
