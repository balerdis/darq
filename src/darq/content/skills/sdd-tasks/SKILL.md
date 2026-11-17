---
name: sdd-tasks
description: "Break an SDD change into implementation tasks. Trigger: orchestrator launches task planning for a change."
disable-model-invocation: true
user-invocable: false
license: MIT
metadata:
  author: darq-balerdis
  version: "2.0"
  delegate_only: true
---

> **ORCHESTRATOR GATE.** Whoever opens this file with the `skill()` tool is the orchestrator, and must not
> run the phase inline: halt here and launch the `sdd-tasks` sub-agent through the platform's delegation
> primitive (`task(...)`, sub-agent invocation, and so on). What follows is for executors only.

## For the sdd-tasks sub-agent

That gate is for the orchestrator, not for you. Do the phase yourself, delegating NONE of it and never
invoking the Skill tool: executing is your job, so execute.

## Artifact language

- Default: English, for every generated technical artifact. Neither the conversation's own language nor the
  persona's regional voice carries into an SDD artifact, unless the user explicitly asks for that artifact
  language or a project convention requires it.
- A language the user explicitly asked for is written neutrally and professionally, unless the user
  explicitly asks for a particular tone or a regional variant.
- Comments meant for the public or for a specific context take that context's language by default. Whatever
  the user says explicitly about language or tone wins; short of that they stay neutral and professional,
  unless their context plainly needs another tone or a regional variant.

## Your job

Three artifacts in, one out. The proposal, the specs and the design go in; `tasks.md` comes out, holding the
TASK BREAKDOWN of the change: implementation steps concrete enough to act on, grouped into phases.

The brief that launches you names three things: the change, the artifact store mode (one of
`engram | openspec | hybrid | none`), and the delivery strategy (one of
`ask-on-risk | auto-chain | single-pr | exception-ok`).

## Inputs and outputs per store mode

Fetching follows **Section B** of `_shared/sdd-phase-common.md`; saving follows its **Section C**. For this
phase the modes mean:

- `engram`: all three inputs are required. Fetch `sdd/{change-name}/proposal`, `sdd/{change-name}/spec` and
  `sdd/{change-name}/design`; the result is saved as `sdd/{change-name}/tasks`.
- `openspec`: do what `_shared/openspec-convention.md` prescribes, after reading it.
- `hybrid`: honor both conventions together: the Engram save and a `tasks.md` on disk. Inputs come from
  Engram first; the filesystem is the fallback.
- `none`: hand the result back and nothing more; no project file is created or changed.

## Procedure

1. **Skills.** Load them as **Section A** of `_shared/sdd-phase-common.md` describes.
2. **Mine the design.** Pull four things out of it: each file it creates, modifies or deletes; the sequence
   the work has to follow, given what depends on what; what every component needs tested; and every
   applicable threat-matrix case, together with the RED test planned for it. Any row explicitly marked `N/A`
   is left out.
3. **Write the tasks.** Shape them by "Phases and tasks", size them by "Sizing the review", and lay them out
   as "The tasks.md template" at the end of this file shows. Under `openspec` or `hybrid` the result is the
   file `openspec/changes/{change-name}/tasks.md`, next to the `proposal.md`, `specs/` and `design.md` that
   change directory already holds. Under `engram` or `none` no `openspec/` directory, and no file inside
   one, gets created: the tasks stay in memory until step 4.
4. **Persist. This step is mandatory and is never skipped.** Apply **Section C** of
   `_shared/sdd-phase-common.md` with artifact `tasks`, topic_key `sdd/{change-name}/tasks`, and type
   `architecture`.
5. **Report** to the orchestrator in the shape of the next section, wrapped in the return envelope that
   **Section D** of `_shared/sdd-phase-common.md` defines.

## What you send back

```markdown
## Tasks Created

**Change**: {change-name}
**Location**: `openspec/changes/{change-name}/tasks.md` (openspec/hybrid) | Engram `sdd/{change-name}/tasks` (engram) | inline (none)

### Breakdown
| Phase | Tasks | Focus |
|-------|-------|-------|
| Phase 1 | {count} | {name of that phase} |
| Phase 2 | {count} | {name of that phase} |
| Phase 3 | {count} | {name of that phase} |
| Total | {sum of the counts} | |

### Implementation Order
{The sequence you recommend, and briefly the reason for it}

### Review Workload Forecast
- Estimated changed lines: {one figure, or a low-high range}
- 400-line budget risk: {Low | Medium | High}
- Chained PRs recommended: {Yes | No}
- Delivery strategy: {ask-on-risk | auto-chain | single-pr | exception-ok}
- Decision needed before apply: {Yes | No}
- Suggested work-unit PR split: {the planned PRs in a few words, or "Not needed"}

### Next Step
{One of two: implementation can start (sdd-apply), or the user first has to say whether chained PRs are wanted, and only then sdd-apply.}
```

## Phases and tasks

The usual run of phases is below; Phase 5 exists only when something is left to clean up.

| Phase | What goes into it |
|---|---|
| 1, Foundation / Infrastructure | whatever later tasks build on: new types and interfaces, config, database changes |
| 2, Core Implementation | the bulk of the change: its main logic, its business rules, its core behavior |
| 3, Integration / Wiring | what makes the parts work as one: connected components, routes, UI wiring |
| 4, Testing | unit, integration and e2e tests, checked against the spec scenarios |
| 5, Cleanup | polish, documentation, and the removal of dead code |

Every task MUST have all four of the qualities below; next to each, one task that has it and one that does
not:

- **Specific**. Has it: "Create `src/billing/invoice_total.py` computing the tax-inclusive total". Lacks it:
  "Do billing".
- **Actionable**. Has it: "Add a `refresh()` method to `SessionStore`". Lacks it: "Deal with sessions".
- **Verifiable**. Has it: "Test: `GET /invoices/42` answers 404 for a different tenant". Lacks it: "Check
  that it works".
- **Small**. Has it: a single file, or one logical piece of work. Lacks it: "Build the whole feature".

What every task list obeys besides:

- A task names concrete file paths, ALWAYS; a task as vague as "implement feature" or "add tests" is NEVER
  acceptable.
- The order MUST follow the dependencies: nothing in Phase 1 should lean on Phase 2.
- Numbering is hierarchical: 1.1, 1.2, then 2.1, 2.2, and on from there.
- A task should fit inside ONE session; split any that feels bigger than that.
- Testing tasks should point at named scenarios in the specs.
- An applicable threat-matrix case MUST become a RED-test task of its own, ahead of the production task it
  guards, carrying the case and its expected safe/failure behavior exactly as the design states them. A row
  marked `N/A` produces no task.
- A project that uses TDD gets the test-first sequence built into its tasks: a RED task writes the failing
  test, a GREEN task makes it pass, a REFACTOR task tidies up.
- `rules.tasks` in `openspec/config.yaml`, when present, applies here too.
- Size: the tasks artifact MUST stay under 530 words. Write a checklist, never paragraphs, with each task one
  or two lines long at most.

## Sizing the review

The review budget is **400 changed lines**, counted as `additions + deletions`. Before the list is final,
judge how likely the implementation is to exceed it. This is a guard on the plan, not a count of the diff
to come. The evidence is what you can see: how many files and how many phases, every point where parts
integrate, tests and docs, generated artifacts and migrations, and the number of separate concerns the
change cuts across.

The forecast goes in EVERY time, near the top of the artifact so the user meets it before implementation
starts, and never folded into prose. Its table is welcome for readability, but what the downstream guards
match, literally, are four plain-text lines. The forecast MUST carry them exactly, as bare lines the way the
template shows:

- `Decision needed before apply: Yes|No`
- `Chained PRs recommended: Yes|No`
- `Chain strategy: stacked-to-main|feature-branch-chain|size-exception|pending`
- `400-line budget risk: Low|Medium|High`

Work units are owed evidence whatever the estimate: each suggested unit MUST name its Focused test command,
its Runtime harness command or scenario (or an explicit `N/A` reason), and its Rollback boundary.

### A High estimate

When the risk is High, or the work will probably land above 400 lines:

1. Set `Chained PRs recommended` to `Yes`.
2. Cut the tasks into **work units**, each of which can turn into one PR of a chain or a stack.
3. Give every suggested PR its own clear start and clear finish, its own verification, a scope that needs
   nothing else to make sense, a focused test command, a runtime harness, and a rollback boundary.
4. **Ask the user** which chain strategy to follow; that choice belongs to the team.
   - `stacked-to-main` lands each PR on main in turn. Fast iteration, fixes made on the way; right for
     teams that want speed first, and for slices independent of one another.
   - `feature-branch-chain` collects the final integration on a feature/tracker branch. PR #1 targets the
     tracker; every later PR targets the PR immediately before it, so each child diff stays focused; only
     the tracker merges into main. Right when rollback control and coordinated releases matter.
   - `size-exception` keeps one single PR, with a maintainer's approval. Right for generated code,
     migrations, and vendor diffs.
5. Cache what the user chose, and let the delivery strategy you were given decide
   `Decision needed before apply`:

| Delivery strategy | `Decision needed before apply` | What follows |
|---|---|---|
| `ask-on-risk` | `Yes` | the orchestrator asks before apply |
| `auto-chain` | `No` | the orchestrator starts on the first slice with the chosen chain strategy |
| `single-pr` | `Yes` | the orchestrator must require `size:exception` before apply |
| `exception-ok` | `No` | the maintainer has already accepted `size:exception` |

In short: work likely to pass 400 changed lines gets chained PRs recommended in the forecast, and the delivery
strategy you received settles whether a decision or an exception has to come before apply.

### Bases in a feature-branch chain

Whatever the estimate, with `feature-branch-chain`, the suggested work units SHOULD name each unit's base: the feature/tracker
branch for PR #1, the PR #1 branch for PR #2, the PR #2 branch for PR #3. If a child PR's diff still carries
an earlier PR's changes, its base is wrong; retarget or rebase it before anyone reviews it.

## The tasks.md template

```markdown
# Tasks: {Change Title}

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | <approximate figure, or a low-high range> |
| 400-line budget risk | Low / Medium / High |
| Chained PRs recommended | Yes / No |
| Suggested split | <one PR, or the chain written as PR 1 → PR 2 → PR 3, in order> |
| Delivery strategy | <ask-on-risk / auto-chain / single-pr / exception-ok> |
| Chain strategy | <stacked-to-main / feature-branch-chain / size-exception / pending> |

Decision needed before apply: <Yes|No>
Chained PRs recommended: <Yes|No>
Chain strategy: <stacked-to-main|feature-branch-chain|size-exception|pending>
400-line budget risk: <Low|Medium|High>

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | <a deliverable that stands on its own> | PR 1 | <the narrowest command that proves it> | <the real command or scenario that exercises it, or N/A and why> | <the files or behavior that can come out without dragging unrelated work along> |
| 2 | <the next self-contained deliverable> | PR 2 | <the narrowest command that proves it> | <the real command or scenario that exercises it, or N/A and why> | <where it can be reverted independently of the rest> |

## Phase 1: {Phase Name} (for instance Foundation / Infrastructure)

- [ ] 1.1 {A concrete step: the file it touches and the change made there}
- [ ] 1.2 {Another concrete step}
- [ ] 1.3 {Another concrete step}

## Phase 2: {Phase Name} (for instance Core Implementation)

- [ ] 2.1 {Another concrete step}
- [ ] 2.2 {Another concrete step}
- [ ] 2.3 {Another concrete step}
- [ ] 2.4 {Another concrete step}

## Phase 3: {Phase Name} (for instance Verification / Testing)

- [ ] 3.1 {Add tests that cover ...}
- [ ] 3.2 {Add tests that cover ...}
- [ ] 3.3 {Check that ... and ... work together}

## Phase 4: {Phase Name} (for instance Documentation / Cleanup)

- [ ] 4.1 {Bring docs and comments up to date}
- [ ] 4.2 {Delete the temporary code}
```
