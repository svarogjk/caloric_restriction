# Git Rules

## Branch

- Main branch is `main`
- Always pull before pushing: `git pull --rebase origin main`

## Commit Prefixes (Required)

`feat:` | `fix:` | `chore:` | `refactor:` | `docs:` | `test:`

## Commit Rules

1. Imperative mood: "add feature" not "added feature"
2. First line under 72 characters
3. Add `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` to Claude-assisted commits
4. Stage specific files, never `git add -A` or `git add .`

## Safety

- **NEVER** force push to main
- **NEVER** `git reset --hard` without permission
- **NEVER** commit `.env` or credentials
- **NEVER** skip hooks (`--no-verify`)
- **ALWAYS** create NEW commits, never amend unless explicitly asked
- **NEVER** create a commit autonomously — only the user may trigger commits

## Tags

Semantic versioning: `git tag -a vMAJOR.MINOR.PATCH -m "description"`
