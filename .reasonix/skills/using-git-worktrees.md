---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans
---
# Using Git Worktrees (Reasonix Port)

Ensure work happens in an isolated workspace using git worktrees.

**Core principle:** Detect existing isolation first. Create if needed. Never fight the harness.

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

## Step 0: Detect Existing Isolation

Check if already in a linked worktree:

```bash
git rev-parse --git-dir
git rev-parse --git-common-dir
BRANCH=$(git branch --show-current)
```

**If git-dir != git-common-dir (and not in a submodule):** Already in a linked worktree. Skip to Step 3.

**If git-dir == git-common-dir (or in a submodule):** Normal repo checkout. Proceed to Step 1.

## Step 1: Create Isolated Workspace

Since no native worktree tool is available (Reasonix doesn't provide one), use git worktree fallback:

### Directory Selection

Check for existing worktree directories:
```bash
ls -d .worktrees 2>/dev/null   # Preferred (hidden)
ls -d worktrees 2>/dev/null    # Alternative
```

If neither exists, default to `.worktrees/`.

### Safety Verification

```bash
git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
```

If NOT ignored, add to `.gitignore` first.

### Create the Worktree

```bash
git worktree add .worktrees/<branch-name> -b <branch-name>
cd .worktrees/<branch-name>
```

### Sandbox Fallback

If `git worktree add` fails (permission/sandbox denial), tell the user and work in the current directory instead.

## Step 3: Project Setup

Auto-detect and run setup:

```bash
# Node.js
if [ -f package.json ]; then npm install; fi
# Python
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
if [ -f pyproject.toml ]; then pip install -e .; fi
# Rust
if [ -f Cargo.toml ]; then cargo build; fi
# Go
if [ -f go.mod ]; then go mod download; fi
```

## Step 4: Verify Clean Baseline

Run tests to ensure workspace starts clean:

```bash
npm test / cargo test / pytest / go test ./...
```

**If tests fail:** Report failures, ask whether to proceed or investigate.
**If tests pass:** Report ready.
