---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---
# Writing Plans (Reasonix Port)

Write comprehensive implementation plans. Document everything needed: which files to touch for each task, complete code, testing, how to verify. Give the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume the executor knows almost nothing about the toolset or problem domain.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Save plans to:** `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`

## Scope Check

If the spec covers multiple independent subsystems, suggest breaking into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for:
- Design units with clear boundaries and well-defined interfaces
- Prefer smaller, focused files over large ones that do too much
- Files that change together should live together
- In existing codebases, follow established patterns

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement minimal code to pass" — step
- "Run tests to verify pass" — step
- "Commit" — step

## Task Structure

Each task should follow this pattern:

```
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**
  ```python
  def test_specific_behavior():
      assert function(input) == expected
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/path/test.py::test_name -v`
  Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
  (complete code shown)

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/path/test.py::test_name -v`
  Expected: PASS

- [ ] **Step 5: Commit**
```

## No Placeholders

Every step must contain the actual content. These are **plan failures**:
- "TBD", "TODO", "implement later"
- "Add appropriate error handling" (without specifics)
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code)
- Steps that describe WHAT without showing HOW

## Self-Review

After writing the complete plan:

1. **Spec coverage:** Can you point to a task that implements each requirement?
2. **Placeholder scan:** Search for red flags. Fix them.
3. **Type consistency:** Do signatures and names match across tasks?

## Execution Handoff

After saving the plan, present execution options:

**"Plan complete and saved. Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch subagents per task with 2-stage review
**2. Inline Execution** — execute tasks directly with checkpoints

**Which approach?"**

**If Subagent-Driven:** Use `subagent-driven-development` skill
**If Inline:** Use `executing-plans` skill
