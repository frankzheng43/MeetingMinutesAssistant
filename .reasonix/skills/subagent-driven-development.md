---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks - dispatches subagents per task with 2-stage review
---
# Subagent-Driven Development (Reasonix Port)

Execute plan by dispatching subagents per task, with two-stage review after each: spec compliance review first, then code quality review.

**Core principle:** Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration

**Continuous execution:** Do not pause to check in with your human partner between tasks. Execute all tasks without stopping. The only reasons to stop: BLOCKED status you cannot resolve, ambiguity, or all tasks complete.

## The Process

### Setup
1. Read the plan file, extract all tasks with full text
2. Create `todo_write` with all tasks

### Per Task

For each task, run this cycle:

**1. Dispatch Implementer Subagent**

Use `explore` as a subagent (or your platform's subagent tool) with the following structure:

```
Task: Implement Task N: [task name]

Full task text: [paste complete task including all code]

Context: [where this fits, dependencies, architectural context]

Instructions:
- Implement exactly what the task specifies
- Follow TDD if the task says to
- Write tests, verify, commit
- Self-review before reporting
- Report status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT

If you have questions, ask them before starting work.
```

**2. Handle Implementer Status**

- **DONE:** Proceed to spec compliance review
- **DONE_WITH_CONCERNS:** Read concerns before proceeding. If about correctness, address first.
- **NEEDS_CONTEXT:** Provide missing context and re-dispatch
- **BLOCKED:** Assess the blocker, provide more context, use a more capable model, or break the task down

**3. Spec Compliance Review**

Review the implementation against the requirements:
- Did they implement everything requested?
- Did they build things not requested (over-engineering)?
- Did they misinterpret requirements?

Use `review` or manual code reading to verify. Fix any spec gaps before proceeding.

**4. Code Quality Review**

Review for code quality:
- Clean architecture
- Good test coverage
- Following project patterns
- No magic numbers, no duplication

Fix any important issues. Proceed to next task.

**5. Mark Task Complete**

Use `todo_write` to mark the task as completed.

### After All Tasks

Dispatch a final code review for the entire implementation, then use `finishing-a-development-branch`.

## Model Selection

- **Mechanical tasks** (isolated functions, clear specs, 1-2 files): use fast/cheap model
- **Integration tasks** (multi-file coordination): use standard model
- **Review tasks**: use the most capable available model

## Red Flags

**Never:**
- Skip either review stage
- Proceed with unfixed issues
- Dispatch multiple implementation subagents in parallel (conflicts)
- Ignore subagent questions
- Start code quality review before spec compliance is ✅

**If reviewer finds issues:** Implementer fixes them, reviewer reviews again. Repeat until approved.
