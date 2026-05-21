---
name: dispatching-parallel-agents
description: Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
---
# Dispatching Parallel Agents (Reasonix Port)

When you have multiple unrelated failures or independent tasks, investigating them sequentially wastes time. Dispatch them in parallel.

**Core principle:** One agent per independent problem domain. Let them work concurrently.

## When to Use

**Use when:**
- 3+ test files failing with different root causes
- Multiple subsystems broken independently
- Each problem can be understood without context from others
- No shared state between investigations

**Don't use when:**
- Failures are related (fix one might fix others)
- Need to understand full system state
- Agents would interfere with each other (editing same files)

## The Pattern

### 1. Identify Independent Domains

Group failures by what's broken:
- File A tests: Tool approval flow
- File B tests: Batch completion behavior
- File C tests: Abort functionality

Each domain is independent.

### 2. Dispatch in Parallel

Use the `explore` skill (or platform subagent tool) for each domain simultaneously:

```
run_skill({name: "explore", arguments: "Investigate and fix 3 failing tests in path/to/test/file.test.ts..."})
```

Since `explore` runs in an isolated subagent, multiple can run concurrently.

### 3. Review and Integrate

When agents return:
- Read each summary
- Verify fixes don't conflict
- Run full test suite
- Integrate all changes

## Agent Prompt Structure

Good prompts are:
1. **Focused** — One clear problem domain
2. **Self-contained** — All context needed
3. **Specific about output** — What should the agent return?

**Bad:** "Fix all the tests" — too broad
**Good:** "Fix the 3 failing tests in agents/agent-tool-abort.test.ts — here are the specific failures..."

## When NOT to Use

- **Related failures:** Fixing one might fix others — investigate together first
- **Need full context:** Requires seeing entire system
- **Exploratory debugging:** You don't know what's broken yet
- **Shared state:** Agents would interfere (editing same files)

## Verification

After agents return:
1. Review each summary
2. Check for conflicts (did agents edit same code?)
3. Run full suite to verify all fixes work together
4. Spot check — agents can make systematic errors
