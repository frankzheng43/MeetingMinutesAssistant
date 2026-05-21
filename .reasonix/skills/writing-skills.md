---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---
# Writing Skills — Reasonix Edition

**Writing skills is TDD applied to process documentation.**

You write test cases (pressure scenarios), watch them fail (baseline behavior), write the skill, watch tests pass, and refactor (close loopholes).

**Core principle:** If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.

## How to Create a Skill in Reasonix

Use `install_skill` (or `create_skill`) to create a new playbook:

```javascript
install_skill({
  name: "skill-name",
  description: "Use when [triggering conditions]",
  body: "# Skill Name\n\nFull markdown playbook...",
  scope: "project",    // or "global"
  runAs: "inline",     // or "subagent" for isolated tasks
})
```

## Skill Anatomy

A good skill has:
- **Frontmatter**: `name` (letters, digits, hyphens) + `description` (starts with "Use when...", describes triggering conditions only — NOT what the skill does)
- **Overview**: Core principle in 1-2 sentences
- **When to Use**: Specific symptoms and situations
- **Process**: Step-by-step instructions
- **Common Mistakes / Red Flags**: What to watch out for

## Critical: Description = When, NOT What

**The description should ONLY describe triggering conditions.** Do NOT summarize the skill's process or workflow in the description.

Why: Testing revealed that when a description summarizes the workflow, the agent may follow the description instead of reading the full skill content.

```yaml
# ✅ GOOD: Triggering conditions only
description: Use when implementing any feature or bugfix, before writing implementation code

# ❌ BAD: Summarizes workflow
description: Use for TDD - write test first, watch it fail, write minimal code, refactor
```

## Inline vs Subagent

- **Inline** (`runAs: "inline"`): The skill body is appended to your context. Use for methodology/decision guides you need to follow yourself.
- **Subagent** (`runAs: "subagent"`): Spawns an isolated agent. Use for tasks that would flood your context (deep exploration, multi-step research).

## Bulletproofing Skills Against Rationalization

Skills that enforce discipline need to resist rationalization. Agents are smart and will find loopholes:

1. **Close every loophole explicitly** — Don't just state the rule, forbid specific workarounds
2. **Address "spirit vs letter" arguments** — Add: "Violating the letter of the rules is violating the spirit"
3. **Build a rationalization table** — Every excuse agents make goes in a table
4. **Create a Red Flags list** — Make it easy to self-check when rationalizing

## Quality Checklist

- [ ] Description starts with "Use when..." with specific triggers
- [ ] No workflow summary in description
- [ ] Clear overview with core principle
- [ ] Process steps are actionable
- [ ] Common mistakes section
- [ ] Red flags section (for discipline skills)
- [ ] One good example (not multi-language)
- [ ] Tested before deployment
