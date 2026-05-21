---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
---
# Systematic Debugging (Reasonix Port)

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## The Four Phases

### Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

1. **Read Error Messages Carefully**
   - Don't skip past errors or warnings
   - Read stack traces completely
   - Note line numbers, file paths, error codes

2. **Reproduce Consistently**
   - Can you trigger it reliably?
   - What are the exact steps?
   - If not reproducible → gather more data, don't guess

3. **Check Recent Changes**
   - What changed that could cause this?
   - Check git diff, recent commits, new dependencies, config changes

4. **Gather Evidence in Multi-Component Systems**

   When the system has multiple components (API → service → database, CI → build → deploy):
   
   For EACH component boundary, log what enters and exits. Check environment/config at each layer. Run once to gather evidence, THEN analyze.

5. **Trace Data Flow**

   When error is deep in call stack:
   - Where does the bad value originate?
   - What called this with the bad value?
   - Keep tracing up until you find the source
   - **Fix at source, not at symptom**

### Phase 2: Pattern Analysis

1. Find working examples in the same codebase
2. Compare against references — read them completely
3. Identify differences between working and broken
4. Understand dependencies, config, environment

### Phase 3: Hypothesis and Testing

1. Form a single hypothesis: "I think X is root cause because Y"
2. Test minimally — smallest possible change, one variable at a time
3. Verify: Did it work? Yes → Phase 4. No → new hypothesis.

### Phase 4: Implementation

1. Create a failing test that reproduces the bug
2. Implement a single fix addressing root cause
3. Verify: test passes, no regressions
4. If fix doesn't work after 3 attempts: STOP and question the architecture

**After 3+ failed fixes:** Stop and question fundamentals. Is the pattern fundamentally sound? Should the architecture be refactored? Discuss with your human partner.

## Red Flags — STOP

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "One more fix attempt" (when already tried 2+)

**ALL of these mean:** STOP. Return to Phase 1.

## When Process Reveals "No Root Cause"

If systematic investigation reveals the issue is environmental, timing-dependent, or external:
1. Document what you investigated
2. Implement appropriate handling (retry, timeout, error message)
3. Add monitoring/logging

**But:** 95% of "no root cause" cases are incomplete investigation.
