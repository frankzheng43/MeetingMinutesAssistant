---
name: executing-plans
description: Use when you have a written implementation plan to execute inline with review checkpoints
---
# Executing Plans (Reasonix Port)

Load plan, review critically, execute all tasks, report when complete.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

**Note:** If subagents are available, use `subagent-driven-development` instead — it produces higher quality results with fresh context per task.

## The Process

### Step 1: Load and Review Plan
1. Read the plan file from `docs/superpowers/plans/`
2. Review critically — identify any questions or concerns
3. If concerns: Raise them before starting
4. If clear: Create `todo_write` with all tasks and proceed

### Step 2: Execute Tasks

For each task:
1. Mark as `in_progress` via `todo_write`
2. Follow each step exactly (the plan has bite-sized steps)
3. Run verifications as specified
4. Mark as `completed` via `todo_write`

### Step 3: Complete Development

After all tasks complete and verified:
- Use `finishing-a-development-branch` skill via `run_skill({name: "finishing-a-development-branch", arguments: "<summary>"})`

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## Remember
- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Reference skills when plan says to
- Stop when blocked, don't guess
