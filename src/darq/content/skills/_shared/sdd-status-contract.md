# Change Status Contract

Before an SDD command or phase skill acts on a change, the change's state is written down as
structured status, so that orchestration never has to guess the state, the paths or the edit scope.
The SDD commands and the phase skills share this contract, written in the OpenSpec style.

## When status is required

A command that selects, continues, applies, verifies or archives an SDD change MUST, before anything
else, produce structured status or consume status already produced. That status is what passes
from the orchestrator to the executor of the phase.

Before it launches an executor or does any archive work, every command that acts on a change MUST show:

- which change is active, and how that was decided;
- the status of each artifact, and the paths or topics used as context;
- task progress, plus the list of unchecked tasks whenever tasks exist;
- the next recommended action;
- `blockedReasons` whenever `nextRecommended` is anything but `verify`, together with any blocker on
  the edit roots.

## Which change

1. A change name was given: use exactly that change, once you have confirmed it exists in whichever
   artifact store was selected.
2. No name was given: infer one only if session state leaves no doubt about the active change, or if
   exactly one change is active.
3. More than one active change fits, or which one is active is unclear: let the user pick. Never
   guess.
4. Nothing is active: say there is no active SDD change, with `/sdd-new <change>` as the suggestion.

## Building status by hand

When local native review is disabled, do NOT invoke or trust a status dispatcher left behind by an
earlier installation. Assemble the status schema yourself from the artifact backend the
session selected: the OpenSpec files under `openspec`, the Engram topics under `engram`, and both
selected stores under `hybrid`.

Routing to archive takes four things: completed persisted tasks, completed apply-progress, a current
passing fresh-context `sdd-verify` report, and no unresolved implementation or test blocker. Local
archive routing needs no native review receipt, ledger, bundle, context, state or gate. A complete artifact set
whose terminal receipt is missing routes to `archive`, not to `resolve-review`.

## The schema

Status is markdown that carries the fields below; a host that supports JSON may get the same fields
as JSON instead.

```yaml
schemaName: DARQ baseline.sdd-status
schemaVersion: 1
changeName: <change-name-or-null>
artifactStore: openspec | engram | hybrid
planningHome:
  mode: repo-local
  path: <absolute path to openspec>
changeRoot: <absolute path to openspec/changes/<change> or null>
artifactPaths:
  proposal: [<absolute path>]
  specs: [<absolute paths>]
  design: [<absolute path>]
  tasks: [<absolute path>]
  applyProgress: [<absolute path>]
  verifyReport: [<absolute path>]
contextFiles:
  proposal: [<absolute readable files>]
  specs: [<absolute readable files>]
  design: [<absolute readable files>]
  tasks: [<absolute readable files>]
  applyProgress: [<absolute readable files>]
  verifyReport: [<absolute readable files>]
artifacts:
  proposal: missing | done | partial
  specs: missing | done | partial
  design: missing | done | partial
  tasks: missing | done | partial
  applyProgress: missing | done | partial
  verifyReport: missing | done | partial
taskProgress:
  total: 0
  completed: 0
  pending: 0
  allComplete: false
dependencies:
  proposal: blocked | ready | all_done
  specs: blocked | ready | all_done
  design: blocked | ready | all_done
  tasks: blocked | ready | all_done
  apply: blocked | ready | all_done
  verify: blocked | ready | all_done
  archive: blocked | ready | all_done
applyState: blocked | all_done | ready
actionContext:
  mode: repo-local
  workspaceRoot: <absolute path>
  allowedEditRoots: [<absolute paths>]
relationships:
  dependsOn: []
  supersedes: []
  amends: []
  conflictsWith: []
  sameDomainActiveChanges: []
phaseInstructions:
  apply: [<instruction strings>]
  verify: [<instruction strings>]
  remediate: [<instruction strings>]
  archive: [<instruction strings>]
nextRecommended: propose | spec | design | tasks | apply | verify | archive | sdd-new | select-change | resolve-blockers
blockedReasons: []
```

- Optional: `phaseInstructions`, which only appears if instructions were requested. It holds the
  keys of the execution phases, `apply`, `verify` and `archive`; the planning phases' instructions, for
  `propose`, `spec`, `design` and `tasks`, are carried by markdown from the dispatcher instead.
- An empty path field MUST be an array, never null.
- `changeRoot` and `changeName` may be null. Every other section that is not optional should still
  be there in output built as a fallback, so that consumers read status built natively and status
  built by hand the same way.

## What `applyState` means

| Value | When |
|---|---|
| `blocked` | the artifacts apply needs are missing, it is ambiguous which tasks to take, or editing is unsafe given the action context |
| `all_done` | there is a tasks artifact, and all of its implementation tasks are checked `[x]` |
| `ready` | there is a tasks artifact with one or more implementation tasks still unchecked, and it is safe to edit within the scope |

## What `dependencies` means

- For `proposal`, `specs`, `design` and `tasks`, the value says which of blocked, ready and all done
  applies, given the artifacts each one depends on.
- `apply` can be `ready` only while specs, design and tasks are on hand and the tasks are not all
  done.
- `verify` can be `ready` only after every task is complete. Verification judges requirements, tests
  and the impact of the change, and needs no review transaction, receipt or ledger to do it. A
  failed verification sends the work back to the implementation it concerns, and a fresh
  `sdd-verify` is the only normal verification authority.
- `archive` can be `ready` only with completed persisted tasks, completed apply-progress, a current
  passing fresh-context `sdd-verify` report and no unresolved implementation or test blocker. No
  native review artifact and no review gate is required for it.

## Edit scope

`actionContext` goes into every phase launch; carrying it there is a MUST for the orchestrator.

- Context rebuilt by hand that fails to prove who owns the edits, or which edit roots are allowed,
  means: do not edit at all.
- With `allowedEditRoots` present, nothing outside those roots is edited.
- A command unable to prove that a file lies within the authoritative workspace, or within the
  allowed edit roots, halts and asks the user to clarify.
