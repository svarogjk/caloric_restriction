# Git Rules

Rules for all git operations in this project.

## Branch

- Main branch is `development`
- Always pull before pushing
- Use rebase for clean history: `git pull --rebase origin development`

## Commit Prefixes (Required)

| Prefix | Use |
|--------|-----|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `chore:` | Maintenance, deps |
| `refactor:` | Code restructure |
| `docs:` | Documentation |
| `test:` | Tests |

## Commit Rules

1. Use imperative mood: "add feature" not "added feature"
2. Keep first line under 72 characters
3. Add `Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>` to Claude-assisted commits
4. Stage specific files, never use `git add -A` or `git add .`

## Safety Rules

1. **NEVER** force push to development
2. **NEVER** use `git reset --hard` without permission
3. **NEVER** commit `.env` or credentials
4. **NEVER** skip pre-commit hooks (`--no-verify`)
5. **ALWAYS** create NEW commits, never amend unless explicitly asked

## Tags

Semantic versioning: `vMAJOR.MINOR.PATCH`

```bash
git tag -a v1.0.0 -m "Release description"
git push origin v1.0.0
```
