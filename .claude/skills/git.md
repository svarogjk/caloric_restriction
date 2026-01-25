# Git Skill

Use this skill when working with git operations, commits, branches, tags, or version control workflows.

## Branch Strategy

- **Main branch:** `development`
- **Feature branches:** `feature/<name>` (optional, for large features)
- **Hotfix branches:** `hotfix/<name>` (optional, for urgent fixes)

## Conventional Commits

All commits use prefixes to categorize changes:

### Prefix Reference

| Prefix | Description | Example |
|--------|-------------|---------|
| `feat:` | New feature | `feat: add volcano plot component` |
| `fix:` | Bug fix | `fix: correct p-value calculation` |
| `chore:` | Maintenance | `chore: update dependencies` |
| `refactor:` | Code restructure | `refactor: simplify GEO client` |
| `docs:` | Documentation | `docs: update API examples` |
| `test:` | Test changes | `test: add Cox regression tests` |
| `style:` | Formatting | `style: fix linting errors` |
| `perf:` | Performance | `perf: optimize dataset loading` |

### Message Format

```
<prefix>: <imperative description>

[optional body explaining why]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

**Good examples:**
- `feat: add Kaplan-Meier confidence intervals`
- `fix: handle missing survival metadata gracefully`
- `chore: bump lifelines to 0.28.0`

**Bad examples:**
- `updated stuff` (no prefix, vague)
- `feat: Added feature` (past tense, not imperative)
- `FIX: bug` (uppercase, too vague)

## Semantic Versioning

Tags follow semver: `vMAJOR.MINOR.PATCH`

| Version Bump | When |
|--------------|------|
| MAJOR (v2.0.0) | Breaking API changes |
| MINOR (v1.1.0) | New features, backward compatible |
| PATCH (v1.0.1) | Bug fixes, backward compatible |

### Tagging Commands

```bash
# Create annotated tag
git tag -a v1.2.3 -m "Release v1.2.3: add multi-dataset analysis"

# Push tag to remote
git push origin v1.2.3

# List all tags
git tag -l

# Delete tag (local and remote)
git tag -d v1.2.3
git push origin --delete v1.2.3
```

## Common Workflows

### Daily Workflow
```bash
# Start of work - sync with remote
git checkout development
git pull --rebase origin development

# After making changes
git status
git add <specific-files>
git commit -m "feat: description"
git push origin development
```

### Feature Workflow
```bash
# Create feature branch
git checkout -b feature/new-analysis development

# Work and commit...
git add <files>
git commit -m "feat: implement new analysis"

# Merge back to development
git checkout development
git pull --rebase origin development
git merge feature/new-analysis
git push origin development

# Clean up
git branch -d feature/new-analysis
```

### Release Workflow
```bash
# Ensure development is clean
git checkout development
git pull --rebase origin development
git status  # Should be clean

# Create release tag
git tag -a v1.2.0 -m "Release v1.2.0: feature description"
git push origin v1.2.0
```

## Files to Never Commit

```gitignore
# Environment and secrets
.env
.env.local
*.pem
*credentials*

# IDE
.idea/
.vscode/

# Build artifacts
__pycache__/
node_modules/
dist/
build/

# Logs
*.log
geo_logs/
```

## Conflict Resolution

```bash
# When pull --rebase has conflicts
git status  # See conflicted files
# Edit files to resolve conflicts
git add <resolved-files>
git rebase --continue

# If rebase is too messy, abort and merge instead
git rebase --abort
git pull origin development  # Regular merge
```
