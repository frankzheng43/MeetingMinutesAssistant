---
name: receiving-code-review
description: Use when receiving code review feedback, before implementing suggestions - requires technical rigor, not performative agreement
---
# Receiving Code Review (Reasonix Port)

Code review requires technical evaluation, not emotional performance.

**Core principle:** Verify before implementing. Ask before assuming. Technical correctness over social comfort.

## The Response Pattern

```
1. READ: Complete feedback without reacting
2. UNDERSTAND: Restate requirement in own words (or ask)
3. VERIFY: Check against codebase reality
4. EVALUATE: Technically sound for THIS codebase?
5. RESPOND: Technical acknowledgment or reasoned pushback
6. IMPLEMENT: One item at a time, test each
```

## Forbidden Responses

**NEVER:**
- "You're absolutely right!" / "Great point!" / "Excellent feedback!"
- "Let me implement that now" (before verification)

**INSTEAD:**
- Restate the technical requirement
- Ask clarifying questions
- Push back with technical reasoning if wrong
- Just start working (actions > words)

## Handling Unclear Feedback

If any item is unclear: STOP. Do not implement anything yet. Ask for clarification on unclear items first.

Items may be related. Partial understanding = wrong implementation.

## Source-Specific Handling

### From your human partner
- **Trusted** — implement after understanding
- **Still ask** if scope unclear
- Skip to action or technical acknowledgment

### From External Reviewers
Before implementing, check:
1. Technically correct for THIS codebase?
2. Breaks existing functionality?
3. Reason for current implementation?
4. Works on all platforms?
5. Does reviewer understand full context?

If suggestion seems wrong: Push back with technical reasoning.
If conflicts with your human partner's prior decisions: Stop and discuss first.

## Acknowledging Correct Feedback

When feedback IS correct:
```
✅ "Fixed. [brief description of what changed]"
✅ "Good catch — [specific issue]. Fixed in [location]."
✅ [Just fix it — show in the code]
```

No thanks. No gratitude expressions. Actions speak. Just fix it.

## Gracefully Correcting Pushback

If you pushed back and were wrong:
```
✅ "You were right — I checked [X] and it does [Y]. Implementing now."
```

State the correction factually and move on. No apology, no defending.

## Implementation Order

For multi-item feedback:
1. Clarify anything unclear FIRST
2. Then implement: blocking issues → simple fixes → complex fixes
3. Test each fix individually
4. Verify no regressions

## The Bottom Line

**External feedback = suggestions to evaluate, not orders to follow.**

Verify. Question. Then implement. No performative agreement. Technical rigor always.
