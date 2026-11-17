---
name: sdd-archive
description: "Archive a completed SDD change by syncing delta specs. Trigger: orchestrator launches archive after implementation and verification."
disable-model-invocation: true
user-invocable: false
license: MIT
metadata:
  author: darq-balerdis
  version: "2.0"
  delegate_only: true
---

> **ORCHESTRATOR GATE**: Reaching this file through the `skill()` tool means you are
> the ORCHESTRATOR, and the orchestrator never runs it. STOP here and leave every
> instruction below unexecuted; hand the phase to the dedicated `sdd-archive`
> sub-agent through the delegation primitive your platform provides (`task(...)`,
> sub-agent invocation and the like, for instance). Only EXECUTORS read on.

## Executor Override

The gate speaks to the orchestrator alone. When you are the `sdd-archive` sub-agent itself, it does not bind you: carry out the phase below yourself. Do not delegate, and do not invoke the Skill tool; executing is your job.

## What This Phase Does

You close the SDD cycle for one change. The delta specs the change carries are folded into the main specs, which are the source of truth, and the change folder is then moved into the archive.

The orchestrator launches you with:

- the change name;
- the artifact store mode, one of `engram | openspec | hybrid | none`;
- the structured status that `_shared/sdd-status-contract.md` defines, which carries artifact paths, task progress, dependency states and actionContext;
- any explicit intentional-archive override text the user or the orchestrator supplied.

## What You Hand Back

Your final answer to the orchestrator is the return envelope of **Section D** in `_shared/sdd-phase-common.md`, carrying this summary in exactly this shape:

```markdown
## Change Archived

**Change**: {change-name}
**Archived to**: openspec/hybrid → `openspec/changes/archive/{YYYY-MM-DD}-{change-name}/` | engram → Engram archive report | none → inline

### Specs Synced
| Domain | Action | Details |
|--------|--------|---------|
| {domain} | Created/Updated | {requirements: added N, modified M, removed K} |

### Archive Contents
- proposal.md ✅
- specs/ ✅
- design.md ✅
- tasks.md ✅ ({N}/{N} tasks done)

### Source of Truth Updated
These main specs describe the behavior as it now is:
- `openspec/specs/{domain}/spec.md`

### SDD Cycle Complete
Planning, implementation, verification and archiving of this change are all done.
The next change can begin.
```

## Gates Before Anything Changes

Three gates stand between you and any task reconciliation, spec sync or folder move.

### Gate 1: verification

Go on only if the change has all of these: completed persisted tasks, a completed apply-progress, a `sdd-verify` report that is current, passing and produced in a fresh context, and no implementation or test blocker left unresolved. The lifecycle here is a local one; native review transactions, receipts, ledgers, gate contexts and review gates play no part in it.

### Gate 2: task completion

Ownership is split. Marking tasks done in the persisted tasks artifact is the job of `sdd-apply`; confirming that the persisted artifact shows the final state before the cycle closes is yours. Spec sync waits until this gate has passed.

Open the tasks artifact first (the full `sdd/{change-name}/tasks` observation under engram, `openspec/changes/{change-name}/tasks.md` under openspec or hybrid) and look for implementation tasks still unchecked (`- [ ]`). Finding even one means:

1. Stop and return `blocked`. Do not sync specs, do not move the change folder, and do not say the SDD cycle is complete.
2. Say in your report that `sdd-apply` has to be rerun or corrected so that it marks the completed tasks in the persisted tasks artifact.
3. The one way past this is an explicit instruction from the orchestrator to reconcile stale checkboxes, and even then only when apply-progress and verify-report prove that every unchecked task really is complete. That repair is exceptional; if you make it, write the exact reason for the reconciliation into the archive report.

The reason is the audit trail: once archived, completed work must never show up as stale unchecked tasks. Your internal todo state proves nothing here, because completion is visible only through the persisted SDD task artifact, the source of truth for it.

### Gate 3: action context

- Structured status reporting `actionContext.mode: workspace-planning` means STOP. Never move workspace changes into a repo-local archive, and never edit linked repos.
- When `allowedEditRoots` is present, every archive operation stays inside those roots.

### Stricter than OpenSpec

OpenSpec by itself lets a change be archived with incomplete artifacts or tasks once the user confirms. The DARQ baseline is stricter by default:

- Incomplete implementation tasks block the archive. The single exception is stale checkboxes whose completion apply-progress/verify-report prove.
- A CRITICAL issue in `verify-report` blocks the archive every time. Do not accept an override for CRITICAL verification issues.
- Normal task completion is not this phase's to own. Checkbox completion belongs to `sdd-apply`; the archive phase may only perform the exceptional, mechanical reconciliation of gate 2, with proof from apply-progress and verify-report.
- Missing proposal, spec or design artifacts are reported. The archive may go on without them only when the user explicitly chooses an intentional partial archive, and the archive report then records what was missing.

## Store Contract

Retrieval works as **Section B** of `_shared/sdd-phase-common.md` describes, and persistence as its **Section C**. Per store, this phase means:

- **engram**: five reads, all of them required:
  - `sdd/{change-name}/proposal`
  - `sdd/{change-name}/spec`
  - `sdd/{change-name}/design`
  - `sdd/{change-name}/tasks`
  - `sdd/{change-name}/verify-report`

  When apply-progress holds a TDD Evidence Ledger, also read the `sdd/{change-name}/apply-evidence/{n}` records that ledger lists. Every observation ID you read goes into the archive report, so the lineage stays traceable, and the report is saved as `sdd/{change-name}/archive-report`.
- **openspec**: read `_shared/openspec-convention.md` and work by it; the spec merge and the archive folder move happen on disk.
- **hybrid**: both conventions at once. The archive report, observation IDs included, is persisted to Engram, and the filesystem merge and folder move are carried out as well.
- **none**: nothing is written or moved. Return a closure summary and nothing else.

## Procedure

**1. Load skills.** Do what **Section A** of `_shared/sdd-phase-common.md` says.

**2. Fold the deltas into the main specs.** Under engram there is nothing to sync on disk: the artifacts live only in Engram, and the archive report of step 5 carries every observation ID for traceability. Under none there is nothing to sync at all. Under openspec or hybrid, take each delta spec found in `openspec/changes/{change-name}/specs/`:

- if `openspec/specs/{domain}/spec.md` already exists, read it and apply the delta to it as "Merge Semantics" below describes;
- if it does not, the file in the change is a full spec rather than a delta: copy `openspec/changes/{change-name}/specs/{domain}/spec.md` straight to `openspec/specs/{domain}/spec.md`.

**3. Move the change into the archive.** Engram has no `openspec/` directory to move, and its archive report is the audit trail; none performs no filesystem operation. Under openspec or hybrid, move the whole `openspec/changes/{change-name}/` folder to `openspec/changes/archive/YYYY-MM-DD-{change-name}/`, where the prefix is today's date in ISO form (`2026-02-16`, say). If `openspec/changes/archive/` does not exist yet, create it.

**4. Check the result.**

- openspec or hybrid: the main specs were updated correctly; the change folder now sits in the archive; the archive holds every artifact (proposal, specs, design, tasks); the archived `tasks.md` has no unchecked implementation task, unless the orchestrator explicitly approved an archive-time stale-checkbox reconciliation backed by apply-progress/verify-report proof; the active changes directory no longer lists this change.
- engram: the archive report records the observation ID of every artifact, and the tasks observation has no unchecked implementation task, with the same single exception of an explicitly approved, proof-backed reconciliation.
- none: nothing was persisted, so there is nothing to check.

**5. Persist the archive report.** Mandatory; never skip this step. Save it per **Section C** of `_shared/sdd-phase-common.md`, as artifact `archive-report` with topic_key `sdd/{change-name}/archive-report` and type `architecture`.

**6. Report back** with the summary and envelope of "What You Hand Back".

## Merge Semantics

A delta lands on an existing main spec section by section:

| Delta section | What happens in the main spec |
|---|---|
| ADDED Requirements | appended to its Requirements section |
| MODIFIED Requirements | replaces the requirement with the same name |
| REMOVED Requirements | deletes the requirement with the same name, once its Reason/Migration is on record |
| RENAMED Requirements | renames the requirement with the same name; its scenarios stay as they were unless the delta also modifies them |

Handle the merge with care:

- A requirement is identified by its name, such as the heading `### Requirement: Session Expiration`.
- Any requirement the delta does not mention survives untouched.
- Markdown formatting and the heading hierarchy stay correct.
- A REMOVED entry is applied only when the delta carries both its `(Reason: ...)` and `(Migration: ...)` notes.
- A RENAMED entry is applied only when the delta names the old and the new requirement explicitly.
- A merge that would be destructive, removing large sections, needs a warning to the orchestrator and its confirmation first.

## Standing Rules

- A verification report with CRITICAL issues means the change is never archived.
- When the user explicitly approves a non-critical partial archive or a stale-checkbox reconciliation, write the exact reason into the archive report and mark the archive intentional-with-warnings.
- Completed work is never archived while `tasks.md` or the tasks observation still shows stale unchecked implementation tasks.
- Delta specs are synced first and the folder is moved afterwards, never the other way round.
- The archive is an audit trail: archived changes are never deleted or modified.
- Whatever `rules.archive` says in `openspec/config.yaml` applies.

## Artifact Language

Every technical artifact this phase generates is written in English, unless the user explicitly asks for that artifact in another language or the project's own convention requires one. Neither the language of your conversation with the user nor the regional voice of the active persona carries over into SDD artifacts on its own.

When another language has been explicitly requested, keep the register neutral and professional; a different tone or a regional variant needs its own explicit request from the user.

A public or contextual comment takes the language of the context it lands in. An explicit choice of language or tone by the user beats that default; without one, stay neutral and professional unless the context plainly calls for another tone or regional variant.
