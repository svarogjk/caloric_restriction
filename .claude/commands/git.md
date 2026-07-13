---
description: Git workflow helper - sync, commit, tag, push with conventional commits
user-invocable: true
---

# Git Command

Manage git operations with conventional commits.

## Based on the user's request, perform one of these operations:

### 1. Sync (Pull Latest)
```bash
git checkout main
git pull --rebase origin main
```

### 2. Status Check
```bash
git status
git log --oneline -5
```

### 3. Commit Changes
First check what's changed:
```bash
git status
git diff
```

Then create a commit with the appropriate prefix:
- `feat:` for new features
- `fix:` for bug fixes
- `chore:` for maintenance
- `refactor:` for restructuring
- `docs:` for documentation
- `test:` for tests

Stage specific files and commit:
```bash
git add <files>
git commit -m "$(cat <<'EOF'
<prefix>: <description>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### 4. Push Changes
```bash
git pull --rebase origin main
git push origin main
```

### 5. Create Tag
```bash
git tag -a v<version> -m "Release v<version>: <description>"
git push origin v<version>
```

### 6. Full Workflow (Commit + Push)
```bash
git status
git add <specific-files>
git commit -m "$(cat <<'EOF'
prefix: message

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git pull --rebase origin main
git push origin main
```

## Usage Examples

`/git sync` -> Pull latest from main
`/git commit the api changes as a fix` -> Stage and commit with `fix:` prefix
`/git push` -> Pull rebase then push
`/git tag v1.2.0` -> Create and push version tag
`/git status` -> Show current git status
