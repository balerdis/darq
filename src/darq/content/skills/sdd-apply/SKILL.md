---
name: sdd-apply
description: "Implement SDD tasks from specs and design. Trigger: orchestrator launches apply for one or more change tasks."
disable-model-invocation: true
user-invocable: false
license: MIT
metadata:
  author: darq-balerdis
  version: "3.0"
  delegate_only: true
---

> **ORCHESTRATOR GATE**: Reaching this text through the `skill()` tool makes you the
> ORCHESTRATOR, so STOP and do not carry these steps out inline. Hand the work to the
> dedicated `sdd-apply` sub-agent with whatever delegation primitive your platform offers
> (e.g., `task(...)`, sub-agent invocation, etc.). Only EXECUTORS act on this skill.

## Executor Override

When you are the `sdd-apply` sub-agent itself, and not the orchestrator, the gate above is not
addressed to you. Carry on with the phase work below in person: do NOT delegate it, and do NOT call
the Skill tool. As the executor, execute.

## Role

This phase is IMPLEMENTATION. You are handed specific tasks out of `tasks.md` and you turn them into
actual code, holding strictly to what the specs and the design say.

## Rules for This Phase

The general implementation rules, namely reading the specs and design, matching conventions, no
freelancing, recording deviations instead of hiding them, stopping when blocked and PR-slice
discipline, are owned by `_shared/implementation-craft.md`. If that reference is missing or
unreadable, rely on your own judgement and say so in your report.

This phase adds:

- ALWAYS consume or produce the structured status before implementing; readiness is never inferred
  from the conversation alone.
- `applyState: blocked` means STOP with no edits, and so does an unsafe `actionContext` or edit
  root.
- In `openspec` mode, tick tasks in `tasks.md` AS you complete them, not in one pass at the end.
- Finished tasks must be visibly `[x]` in the persisted tasks artifact, which you read again
  before returning; internal todos are no evidence of completion.
- Skills are loaded in Step 1, and every loaded skill is followed strictly when you write code.
- Any `rules.apply` in `openspec/config.yaml` applies to your work.
- With Strict TDD Mode active (Step 3), load `sdd-apply/strict-tdd.md` and follow its cycle INSTEAD
  of Step 4: that module's rules OVERRIDE Step 4 entirely.
- The return envelope follows **Section D** of `_shared/sdd-phase-common.md`.

## Inputs

The orchestrator hands you:

- the change name;
- which task(s) to implement, for instance "Phase 1, tasks 1.1-1.3";
- the artifact store mode, one of `engram | openspec | hybrid | none`;
- the structured status described in `_shared/sdd-status-contract.md`, which carries
  `applyState`, `actionContext`, `contextFiles`, `artifactPaths`, `changeRoot`, `planningHome` and
  `schemaName`, as well as task progress and dependency states;
- the delivery strategy together with the workload decision already settled
  (`ask-on-risk | auto-chain | single-pr | exception-ok`), plus the PR slice or `size:exception`
  where one applies.

## Reading and Writing Artifacts

Retrieval works as **Section B** of `_shared/sdd-phase-common.md` describes, and persistence as its
**Section C** does. Per store:

| Store | What you do |
|-------|-------------|
| `engram` | Read `sdd/{change-name}/tasks`, holding on to that observation's ID because you update it later, together with `sdd/{change-name}/proposal`, `sdd/{change-name}/spec` and `sdd/{change-name}/design`; all four are required. A task is marked done with `mem_update(id: {tasks-observation-id}, content: "...")`, and progress is saved under `sdd/{change-name}/apply-progress`. |
| `openspec` | Read `_shared/openspec-convention.md` and follow it. Tick tasks off in `tasks.md` with `[x]`. |
| `hybrid` | Both conventions at once: progress goes to Engram (`mem_update` for the tasks) AND the `[x]` ticks go into `tasks.md` on the filesystem. |
| `none` | Only return the progress. Project artifacts stay untouched. |

## Guard: Status and Workspace

Before you open an implementation file or write a line of code, take in the structured status the
orchestrator passed you, or assemble the equivalent from the artifacts yourself, and act on it:

| When | Then |
|------|------|
| `applyState` is `blocked` | STOP. Return `blocked`, naming the missing artifacts or the unsafe context. |
| `applyState` is `all_done` | Edit nothing; return `success`, setting `next_recommended: sdd-verify` or `sdd-archive` to whichever the dependency state points to. |
| `applyState` is `ready` | Work only on the pending tasks assigned to you. |
| `allowedEditRoots` is empty while `actionContext.mode` is `workspace-planning` | STOP before any edit. Linked repos and folders are planning context you only read. |
| `allowedEditRoots` is present | Touch only files under those roots. When a needed edit lies outside them, STOP and report the unsafe path. |

Take context from `contextFiles` / `artifactPaths` and never from file names you assume. Under
spec-driven OpenSpec those usually point at the proposal, specs, design and tasks.

## Procedure

### Step 1: Load the Project's Skills

Do what **Section A** of `_shared/sdd-phase-common.md` says.

### Step 2: Gather Context

No code gets written until you have:

1. checked that the structured status shows `applyState: ready`;
2. gone through every applicable artifact path or topic that `contextFiles` lists;
3. read in the "Read Before You Write" order of `_shared/implementation-craft.md` (specs, design,
   existing code, conventions).

If that craft reference is missing or unreadable, pick the reading order by your own judgement and
say so in your report. An unreadable craft reference never blocks the phase.

#### Step 2a: Workload Decision Gate

Look for a `Review Workload Forecast` in the tasks artifact. What the budget is, which chain
strategies exist and how a slice stays reviewable all belong to "Keeping a Diff Reviewable" in
`_shared/implementation-craft.md`; this step only enforces the decision.

When the forecast shows `400-line budget risk: High`, `Chained PRs recommended: Yes` or
`Decision needed before apply: Yes` (any one of them is enough), implement nothing until you have
confirmed that the orchestrator or the user gave you a resolved delivery path:

| Delivery path in your prompt | You may go ahead when |
|------------------------------|-----------------------|
| `auto-chain`, or a chained/stacked PR mode that was chosen | always, following the `Chain strategy` recorded in the tasks artifact |
| `exception-ok`, or a single PR with an exception | your prompt states explicitly that the maintainer accepts `size:exception` |
| `single-pr` over the budget | `size:exception` is explicitly recorded in your prompt |

Check the tasks artifact's `Chain strategy` as well. A value of `pending` means the question came
up and was left open, and an open question is not an answer: STOP and return `blocked`.

With neither a delivery decision nor a chain strategy present, write no code: STOP and return
`blocked` with this exact message:

`Workload decision required before apply: estimated work may exceed 400 changed lines. Ask the user which chain strategy to use (stacked-to-main, feature-branch-chain, or size-exception).`

#### Step 2b: Earlier Apply-Progress

Earlier batches may have left progress behind. Look for it before you start:

1. Run `mem_search(query: "sdd/{change-name}/apply-progress")`.
2. On a hit, call `mem_get_observation(id)` for the untruncated content.
3. Work out which tasks it already shows as complete and leave them alone, beginning at the first
   incomplete one, except a task the orchestrator re-opened: that one is work again.
4. Under Strict TDD, read its `## TDD Evidence Ledger` as well. It lists the evidence records of
   earlier batches, and you never open those to edit them or rewrite them (Step 6).
5. Your apply-progress in Step 6 is a MERGE: every task completed before plus every task you
   complete now, in one combined artifact.

**CRITICAL**: once the orchestrator tells you earlier progress exists, reading it is mandatory.
Writing over it unread destroys the completed work of earlier batches for good.

### Step 3: Resolve Strict TDD Mode

Take `Strict TDD Mode` from your brief first. Without it, resolve the mode with "Resolving Strict TDD
Mode" in `_shared/implementation-craft.md`, which also says what a brief with no recognized spelling
means.

The outcome picks the path:

- **active**: STRICT TDD MODE. Read `sdd-apply/strict-tdd.md` and follow it as your Strict TDD
  module.
- **inactive**: STANDARD MODE. Step 4 is your path, and no TDD module gets loaded.

Either way, keep the outcome at hand, because the return summary reports it.

**Key principle**: when the mode is not active, not one TDD instruction is loaded. The file
`sdd-apply/strict-tdd.md` stays unread and unprocessed and costs zero tokens.

The Strict TDD hard gate, its evidence table and the Work Unit Evidence table that every mode
produces are owned by "Test-Driven Discipline" in `_shared/implementation-craft.md`. If that
reference is missing or unreadable, use your own judgement for evidence discipline and say so in
your report; an unreadable craft reference never blocks the phase.

### Step 4: Standard Implementation Loop

This step runs only when Strict TDD Mode is NOT active. Work through the "Standard Task Loop" in
`_shared/implementation-craft.md`, and tick each task `[x]` in the persisted tasks artifact the
moment it is done rather than later.

### Step 5: Tick Completed Tasks

In `tasks.md`, every task you finished changes from `- [ ]` to `- [x]`, so a line such as
`- [ ] 2.1 Add the orders migration` becomes `- [x] 2.1 Add the orders migration`, while tasks you
have not reached keep their `- [ ]`.

### Step 6: Save Progress and Evidence

Never skip this step; it is MANDATORY.

Write apply-progress the way **Section C** of `_shared/sdd-phase-common.md` describes, as artifact
`apply-progress` with topic_key `sdd/{change-name}/apply-progress` and type `architecture`. Bring
the tasks artifact's `[x]` marks up to date too: `mem_update` under engram, a file edit under
openspec or hybrid.

#### Strict TDD: one evidence record per batch

Under Strict TDD, take this batch's TDD Cycle Evidence table (and its safety-net baseline, when the
table carries one) and write it as its OWN artifact BEFORE writing apply-progress. Each batch gets
exactly one record, and that record is written once.

Where it goes:

- **engram**: `topic_key: sdd/{change-name}/apply-evidence/{n}`, with the same title and the `type: architecture`, `scope: project` and `capture_prompt: false` that every SDD artifact uses. The number `{n}` is 1 for the first batch, otherwise one more than the highest batch number in the apply-progress `## TDD Evidence Ledger`.
- **openspec**: a new file `openspec/changes/{change-name}/apply-evidence/{n}.md`, created once.
- **hybrid**: both.
- **none**: nothing persisted; your return summary still carries the table.

Numbering it safely:

- Apply batches are strictly sequential, because the task and progress artifacts are shared state, so no `{n}` is ever handed out while another apply batch is running.
- Never reuse a key. Prove the key is free before writing: under engram, `mem_search` for it and compare titles exactly (a record's title is its key); under openspec, check that the file does not exist.
- A record already sitting at that number that is not in the ledger was left by a batch that stopped after writing its record and before writing apply-progress: add its ledger line too, and take the next free number.
- If the ledger cannot be read, stop and report. A number is never guessed.

Keeping it immutable:

- Once written, a record is never changed: never `mem_update` it, never save again under its key, never edit its file.
- A correction to an earlier record goes into THIS batch's own record, stated as a correction; earlier records stay untouched.
- A task re-opened after it was complete gets new rows in the re-opening batch's own record, marked as re-opened. Its earlier rows stay in their earlier records.

#### Merging apply-progress

Whenever you write apply-progress:

1. If Step 2b found earlier progress, your artifact MUST carry ALL previously completed tasks, with their status copied over, PLUS the ones you completed now.
2. What you write is cumulative: the state of ALL tasks, from ALL batches.
3. The structure stays as it was, and no task completed in an earlier batch may go missing.
4. Under Strict TDD, apply-progress also holds a `## TDD Evidence Ledger`, one line per batch in a fixed format: `{n} | {key} | {observation id or file path} | {task ids} | {date}`. Copy every existing ledger line exactly, never dropping, merging, reordering or rewording one, and append this batch's line. The RED/GREEN rows of new batches belong in their records, never in apply-progress.
5. If the earlier apply-progress holds evidence tables from before the ledger existed, keep those tables exactly as they are inside apply-progress (no compressing, rewording or dropping them) and start the ledger at n=1 with this batch.

### Step 7: Report Back

Before you return, open the persisted tasks artifact again and check that every task you are about
to report as completed shows `[x]` there; one that still shows `- [ ]` gets its checkbox fixed first.
Completion recorded only in internal todos or in apply-progress does not count, so never report
`Ready for verify` in that state.

Once every implementation work unit is finished, hand control back to the parent orchestrator. You
never launch 4R, Judgment Day, a refuter, a correction actor or a scoped validator yourself; when
requirements, tests or change impact need verifying, the parent may delegate a fresh-context
`sdd-verify`.

The orchestrator gets back this report.

```markdown
## Implementation Progress

**Change**: {change-name}
**Mode**: {Strict TDD | Standard}

### Completed Tasks
- [x] {1.1 — what the task does}
- [x] {1.2 — what the task does}

### Files Changed
| File | Action | What Was Done |
|------|--------|---------------|
| `path/to/new_file.ext` | Created | {one-line summary} |
| `path/to/existing_file.ext` | Modified | {one-line summary} |

{Strict TDD Mode only → the TDD Cycle Evidence table defined in sdd-apply/strict-tdd.md, here as return-summary content; the batch's evidence record is where it lives durably}

### Deviations from Design
{Each point where the implementation departs from design.md, and the reason for it. With none, write "None — implementation matches design."}

### Issues Found
{Problems that surfaced while implementing. With none, write "None."}

### Remaining Tasks
- [ ] {a task still open}
- [ ] {another one still open}

### Workload / PR Boundary
- Mode: {single PR | chained PR slice | stacked PR slice | size:exception}
- Current work unit: {the unit's name, or "N/A"}
- Boundary: {where this apply batch begins and where it stops}
- Estimated review budget impact: {short note}

### Status
{N}/{total} tasks complete. {Ready for next batch / Ready for verify / Blocked by X}
```

## Artifact Language

- English is the default for every technical artifact you generate. An SDD artifact does not pick
  up the language of the chat, nor the regional voice of whichever persona is active; it takes
  another language only when the user explicitly asks for that artifact language or the project's
  convention requires it.
- If the user explicitly wants technical artifacts in some other language, keep them in a
  neutral/professional register, unless the user explicitly asks for a different tone or a
  regional variant.
- A public or contextual comment is written, by default, in the language of the context it is
  aimed at. The user's explicit choice of language or tone always overrides that; without one, stay
  neutral/professional unless the target context plainly calls for some other tone or a regional
  variant.

<!-- darq-local:cbm-protocol -->
## Local Codebase Memory Protocol for Implementation

Reach for CBM before writing code whenever the task changes central or shared symbols, public APIs,
controllers or handlers, service methods, routing, persistence flows, or anything else likely to
have callers that are not obvious. Tool priority and the index-repair rule come from
`_shared/mcp/cbm-convention.md`. If that path is missing or unreadable, say so and proceed without
claiming graph evidence; do not invent your own tool order or fallback conditions.

Do NOT call CBM for a simple mechanical edit confined to one file, where the affected surface is
obvious.

## CBM Index Coherence Gate

This gate runs after implementation and before `apply-progress` is persisted, and only when at
least one of these holds: a High workload forecast; chained or exception delivery; structural or
generated changes owned by apply; a public or shared API, route or module boundary owned by apply;
five or more apply-owned files. Never pin a dirty global diff on apply blindly: use the
orchestrator's baseline and the apply-owned manifest when they exist. Once the gate triggers, read
`sdd-apply/references/cbm-index-coherence.md` before you collect any coherence evidence; that file
owns derivation, moderate-first indexing, coverage evidence, escalation, dirty-baseline handling
and `apply-progress` reporting. If it is missing or unreadable, record coherence as unavailable and
claim no index evidence.
<!-- /darq-local:cbm-protocol -->
