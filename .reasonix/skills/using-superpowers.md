---
name: using-superpowers
description: Bootstrap skill - establishes how to find and use skills, requiring skill invocation before any response
---
# Using Superpowers (Reasonix Port)

## The Rule

**Invoke relevant or requested skills BEFORE any response or action.** Even a 1% chance a skill might apply means you should invoke it to check. If it turns out to be wrong for the situation, you don't need to follow it.

### Skill Check Flow

```
User message received → Might any skill apply? (even 1%)
  → Yes → Invoke skill via run_skill → Follow skill exactly
  → No → Respond normally
```

**Skill check comes BEFORE clarifying questions, BEFORE exploring, BEFORE writing code.**

## Red Flags — These thoughts mean STOP

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |

## Skill Priority

When multiple skills could apply:

1. **Process skills first** (brainstorming, debugging) — determine HOW to approach
2. **Implementation skills second** — guide execution

"Let's build X" → brainstorming first, then implementation.
"Fix this bug" → debugging first, then domain skills.

## Skill Types

- **Rigid** (TDD, debugging): Follow exactly. Don't adapt away discipline.
- **Flexible** (patterns): Adapt principles to context.

The skill itself tells you which.

## Available Skills

The following skills are installed. Invoke them by name via `run_skill`:

- **brainstorming** — Design refinement before any creative work
- **writing-plans** — Create detailed implementation plans
- **subagent-driven-development** — Dispatch subagents per task with 2-stage review
- **executing-plans** — Execute plans inline with checkpoints
- **test-driven-development** — RED-GREEN-REFACTOR cycle
- **requesting-code-review** — Dispatch code reviewers
- **receiving-code-review** — Respond to review feedback
- **systematic-debugging** — 4-phase root cause process
- **verification-before-completion** — Evidence before claims
- **using-git-worktrees** — Isolated workspace setup
- **finishing-a-development-branch** — Merge/PR/cleanup decisions
- **dispatching-parallel-agents** — Parallel independent investigations
- **writing-skills** — Create new skills
