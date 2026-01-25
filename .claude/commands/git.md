---
description: Git workflow helper - sync, commit, tag
user-invocable: true
---

# Git Command

Manage git operations with conventional commits.

## What do you want to do?

Based on the user's request, perform one of these operations:

### 1. Sync (Pull Latest)
```bash
git checkout development
git pull --rebase origin development
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

Stage specific files and commit:
```bash
git add <files>
git commit -m "$(cat <<'EOF'
<prefix>: <description>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

### 4. Push Changes
```bash
git pull --rebase origin development
git push origin development
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
git commit -m "prefix: message

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git pull --rebase origin development
git push origin development
```

## Usage Examples

User: `/git sync`
→ Pull latest from development

User: `/git commit the api changes as a fix`
→ Stage and commit with `fix:` prefix

User: `/git push`
→ Pull rebase then push

User: `/git tag v1.2.0`
→ Create and push version tag

User: `/git status`
→ Show current git status and recent commits
