---
name: requesting-code-review
description: Use when completing tasks, implementing major features, or before merging to verify work meets requirements
---
# Requesting Code Review (Reasonix Port)

Get a fresh review of changes to catch issues before they compound.

**Core principle:** Review early, review often.

## When to Request Review

**Mandatory:**
- After each task in subagent-driven development
- After completing a major feature
- Before merge to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## How to Request

Use the built-in `review` or `security_review` subagent skill:

```
review({task: "Review the changes from base_sha to head_sha. Context: [summary of what was built, what it should do]"})
```

Or for security-sensitive changes:

```
security_review({task: "Full review of the current branch diff"})
```

These dispatch an isolated subagent that reads the diff and returns findings.

## Acting on Feedback

- Fix **Critical** issues immediately
- Fix **Important** issues before proceeding
- Note **Minor** issues for later
- Push back if reviewer is wrong (with technical reasoning)

## Red Flags

**Never:**
- Skip review because "it's simple"
- Ignore Critical issues
- Proceed with unfixed Important issues
- Argue with valid technical feedback

**If reviewer wrong:** Push back with technical reasoning. Show code/tests that prove it works.
