---
name: finishing-a-development-branch
description: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work
---
# Finishing a Development Branch (Reasonix Port)

Guide completion of development work by presenting clear options and handling the chosen workflow.

**Core principle:** Verify tests → Detect environment → Present options → Execute choice → Clean up.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## Step 1: Verify Tests

Run the project's test suite — MUST pass before presenting options.

**If tests fail:** Show failures. Stop. Cannot proceed until tests pass.
**If tests pass:** Continue.

## Step 2: Detect Environment

```bash
git rev-parse --git-dir
git rev-parse --git-common-dir
```

- `git-dir == git-common-dir`: Normal repo — standard 4 options
- `git-dir != git-common-dir`, named branch: Standard 4 options + cleanup
- `git-dir != git-common-dir`, detached HEAD: Reduced 3 options (no merge)

## Step 3: Determine Base Branch

```bash
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```

## Step 4: Present Options

**Normal repo and named-branch worktree:**

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work
```

**Detached HEAD:**

```
Implementation complete. You're on a detached HEAD.

1. Push as new branch and create a Pull Request
2. Keep as-is (I'll handle it later)
3. Discard this work
```

## Step 5: Execute Choice

### Option 1: Merge Locally
```bash
git checkout <base-branch>
git pull
git merge <feature-branch>
# Run tests on merged result
git branch -d <feature-branch>
# Clean up worktree if applicable
```

### Option 2: Push and Create PR
```bash
git push -u origin <feature-branch>
gh pr create --title "<title>" --body "Summary of changes"
```
Do NOT clean up worktree — user needs it for PR iteration.

### Option 3: Keep As-Is
Report branch name and path. Preserve everything.

### Option 4: Discard
Get typed "discard" confirmation first. Then force-delete branch and clean up worktree.

## Step 6: Cleanup Workspace (Options 1 & 4 only)

If in a worktree under `.worktrees/` or `worktrees/`:
```bash
cd <main-repo-root>
git worktree remove <worktree-path>
git worktree prune
```

Do NOT clean up harness-owned worktrees or worktrees not created by this skill.
