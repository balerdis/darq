# Implementation Craft

## Scope

Owns how to implement well once the work to do is known — reading before writing, the test-driven
discipline (Strict TDD and its evidence), and keeping a diff reviewable — independent of any
change-lifecycle machinery. An agent with no SDD context can follow this file on its own; it says
nothing about artifact stores, phase envelopes, or how progress is persisted between batches.

## Authority

This file is the canonical owner of the implementation method: the reading order before code is
written, the Strict TDD hard gate and its evidence table, the Work Unit Evidence table required in
every mode, and the review-workload / chained-PR discipline that keeps a diff reviewable. A calling
skill states which tasks are assigned and how progress is tracked; it does not restate how to
implement.

## Read Before You Write

Write no code until you have read, in this order:
1. The specs, which say WHAT the code has to do
2. The design, which says HOW that code is to be structured
3. The code already in the files you will touch, for the patterns it follows today
4. The coding conventions of the project

## Test-Driven Discipline

### Resolving Strict TDD Mode

Resolve the mode once, in this order, and say which step decided it:

1. **A marker in the instructions already in context**, opening no file for it. A marker is a line
   whose whole content is `Strict TDD Mode: enabled` or `Strict TDD Mode: disabled`, or that line
   with its label in bold, `**Strict TDD Mode**: enabled`; no other shape is one. A project's marker
   beats the person's; contradictory markers of unclear origin count as none: say so and go on.
2. **The project flag** `sdd-init` wrote: `strict_tdd` in `openspec/config.yaml`, or Engram's
   `sdd/{project}/testing-capabilities`.
3. **The runner default**: a test runner means active; none means inactive, and say so.

`enabled` without a test runner is inactive, and say so. A brief carrying the marker's spelling has
already resolved the mode; a brief with no spelling this rule recognizes is resolved here, never
silently as standard mode. A change with no behavior to test records `N/A: no behavior changed` as
its gate result, never FAILED.

### Strict TDD Hard Gate (when Strict TDD Mode is active)

- You MUST produce a **TDD Cycle Evidence** table in your return summary and in the batch's evidence record
- Every task row MUST fill three columns in order: RED (the test, written first) → GREEN (the implementation, passing it) → REFACTOR
- If you complete a task WITHOUT writing tests first, mark it as FAILED in the evidence table
- Verification WILL reject the work if the TDD Evidence table is missing or incomplete
- The table is saved once per batch as its own evidence record (`apply-evidence/{n}`), never rewritten; `sdd-apply/SKILL.md` Step 6 owns where it goes

**There is no silent fallback.** If Strict TDD is active, follow it or report failure. Do not
quietly switch to standard mode.

### Work Unit Evidence (all modes)

Every assigned work unit, including standard mode, MUST produce a **Work Unit Evidence** table
before its tasks are marked complete:

| Row | What it has to show |
|---|---|
| The focused test: its command and exact result | the smallest command that proves this unit, with the command itself, its exit/result and the counts that matter |
| The runtime harness: its command/scenario and exact result | the real integration/runtime path; `N/A` is acceptable only when there is no runtime boundary at all, written out explicitly with the reason |
| The rollback boundary | exactly which files/behavior can be reverted while every piece of unrelated work stays in place |

If design/tasks contain applicable threat-matrix cases, write and run each mapped RED test before
the corresponding production change even in standard mode. Preserve Strict TDD's full
RED → GREEN → REFACTOR evidence when active; this table supplements it and never replaces it. Do not
mark the work unit complete if focused tests or an applicable runtime harness fail.

### Standard Task Loop (when Strict TDD Mode is NOT active)

Take the tasks one at a time, and for each:

1. Read what the task says.
2. Read the spec scenarios it relates to; they are its acceptance criteria.
3. Read the design decisions, which limit how you may solve it.
4. Read how the surrounding code is written, and write yours the same way.
5. Write the code.
6. Mark the task complete as soon as it is done.
7. Write down any problem you hit or any deviation you made.

## Keeping a Diff Reviewable

- The default PR review budget is **400 changed lines** (`additions + deletions`), counting authored
  text additions plus deletions only; generated goldens are excluded from that count.
- When the forecast for the assigned work is High risk, or chained/stacked PRs are recommended, or a
  decision is needed before implementing, confirm a resolved delivery path before writing code:
  1. **Chained/stacked PR mode**: implement only the assigned work-unit slice, keep scope autonomous,
     and report the intended PR boundary. Follow the chain strategy (`stacked-to-main` or
     `feature-branch-chain`) for branch targeting.
  2. **Exception**: continue only if it is explicit that the maintainer accepts the size exception.
- Chain strategies:
  - `stacked-to-main`: a PR targets the branch of the PR before it, or `main` once that one has merged.
  - `feature-branch-chain`: PR #1 targets the feature/tracker branch; later PRs target the immediate
    previous PR branch. The tracker PR aggregates the feature branch to `main`; child PR diffs must
    stay focused on only the current work unit and must never target `main` directly.
- If neither a delivery decision nor a chain strategy is available, stop before writing code and ask
  which chain strategy to use rather than guessing.

## Implementation Rules

- Always read specs before implementing — specs are your acceptance criteria
- Always follow the design decisions — don't freelance a different approach
- Always match existing code patterns and conventions in the project
- If you discover the design is wrong or incomplete, note it in your return summary — don't silently deviate
- If a task is blocked by something unexpected, stop and report back
- When applying a chained/stacked PR slice, keep the batch autonomous: one deliverable scope,
  verification included, and a clear rollback boundary
- When applying a size exception, state it explicitly in the progress report and the return summary
- Never implement tasks that weren't assigned to you
