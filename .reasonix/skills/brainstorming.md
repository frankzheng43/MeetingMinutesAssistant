---
name: brainstorming
description: Use before any creative work - creating features, building components, adding functionality. Explores user intent, requirements and design before implementation.
---
# Brainstorming Ideas Into Designs (Reasonix Port)

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design and get user approval.

**HARD GATE:** Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function utility, a config change — all of them. "Simple" projects are where unexamined assumptions cause the most wasted work. The design can be short (a few sentences for truly simple projects), but you MUST present it and get approval.

## Process

Use `todo_write` to track each item, complete them in order:

1. **Explore project context** — check files, docs, recent commits
2. **Ask clarifying questions** — one at a time, understand purpose/constraints/success criteria
3. **Propose 2-3 approaches** — with trade-offs and your recommendation
4. **Present design** — in sections scaled to their complexity, get user approval after each section
5. **Write design doc** — save to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` and commit
6. **Spec self-review** — check for placeholders, contradictions, ambiguity, scope
7. **User reviews written spec** — ask user to review before proceeding
8. **Transition to implementation** — invoke `writing-plans` skill

## The Process Details

**Understanding the idea:**
- Check out the current project state first (files, docs, recent commits)
- Ask questions one at a time to refine the idea
- Prefer multiple choice questions when possible
- Focus on: purpose, constraints, success criteria

**Exploring approaches:**
- Propose 2-3 different approaches with trade-offs
- Present with your recommendation and reasoning
- Lead with your recommended option

**Presenting the design:**
- Scale each section to its complexity (a few sentences if straightforward)
- Ask after each section whether it looks right
- Cover: architecture, components, data flow, error handling, testing

**Design for isolation and clarity:**
- Break the system into smaller units with one clear purpose each
- Each unit should be understandable without reading its internals
- Smaller, well-bounded files make your edits more reliable

**Working in existing codebases:**
- Follow existing patterns
- Include targeted improvements as part of the design
- Don't propose unrelated refactoring

## After the Design

**Documentation:**
- Write the validated spec to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- Commit the design document

**Spec Self-Review:**
1. **Placeholder scan:** Any "TBD", "TODO", or vague requirements? Fix them.
2. **Internal consistency:** Do any sections contradict each other?
3. **Scope check:** Focused enough for one implementation plan?
4. **Ambiguity check:** Could any requirement be interpreted two ways?

**User Review Gate:** Ask the user to review the written spec before proceeding. Only proceed once the user approves.

**Implementation:**
- Invoke the `writing-plans` skill to create a detailed implementation plan via `run_skill({name: "writing-plans", arguments: "<spec summary>"})`

## Key Principles

- **One question at a time** — Don't overwhelm with multiple questions
- **Multiple choice preferred** — Easier to answer than open-ended
- **YAGNI ruthlessly** — Remove unnecessary features from all designs
- **Explore alternatives** — Always propose 2-3 approaches before settling
- **Incremental validation** — Present design, get approval before moving on
