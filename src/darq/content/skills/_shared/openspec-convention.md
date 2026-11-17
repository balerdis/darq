# Working in the openspec Store

How every SDD skill lays out, names and edits files when the artifact store is `openspec` (or the
file half of `hybrid`).

## Layout

Each entry names the phase that writes it.

```
openspec/
├── config.yaml  # sdd-init: per-project SDD settings, keys below
├── specs/  # main specs, the source of truth
│   └── {domain}/
│       └── spec.md
└── changes/  # everything in flight
    ├── archive/  # finished changes, one YYYY-MM-DD-{change-name}/ folder each
    └── {change-name}/  # the folder of one active change
        ├── state.yaml  # orchestrator: DAG state, on disk so a compaction loses nothing
        ├── exploration.md  # sdd-explore, only when it saves one
        ├── proposal.md  # sdd-propose: the proposal
        ├── specs/  # sdd-spec: one delta per domain
        │   └── {domain}/
        │       └── spec.md  # the delta spec
        ├── design.md  # sdd-design: the technical design
        ├── tasks.md  # sdd-tasks: the task list, later ticked by sdd-apply
        ├── apply-evidence/  # sdd-apply, Strict TDD only: {n}.md per batch
        └── verify-report.md  # sdd-verify: the verification report
```

The tree names who writes each file; a few writes need more than a name:

- The orchestrator creates `state.yaml` and keeps it current after that.
- sdd-init creates `openspec/config.yaml` together with the folders `openspec/specs/`,
  `openspec/changes/` and `openspec/changes/archive/`.
- sdd-apply marks each finished task `[x]` in `tasks.md`. Under Strict TDD it also adds
  `openspec/changes/{change-name}/apply-evidence/{n}.md`, a new file per batch that is written
  once and never edited afterwards.
- sdd-archive moves the whole change folder into `openspec/changes/archive/` (see "Once a change
  is archived") and merges each delta into the main spec of its domain, `openspec/specs/{domain}/spec.md`.

A phase reads an artifact from the spot it was written to: the proposal, design, tasks and verify
report inside the change folder, every domain subdirectory of the change's `specs/` for the
deltas, `openspec/config.yaml` for the project settings, and for the main spec of a domain the
same `spec.md` under `openspec/specs/{domain}/` that archive merges into.

## Before writing anything

- The change folder comes first: create it before you write any artifact into it.
- Find an artifact in place? Read it first, then update it there; never overwrite it blind.
- A change folder that has artifacts in it is a change you are continuing, not starting over.
- Per-phase project constraints are taken from the `rules` section of `openspec/config.yaml`.

## Delta spec sections

A delta spec may use any of these four headings, written exactly as shown; each one tells archive
how to change the main spec:

| Heading | Effect on the main spec | What the delta has to contain |
|---|---|---|
| `## ADDED Requirements` | its requirements are appended | the new requirements |
| `## MODIFIED Requirements` | the requirement with the same name is swapped out, block and all | the updated requirement in full (MUST), including each unchanged scenario that must be kept |
| `## REMOVED Requirements` | the requirement with the same name is dropped | for each one a `(Reason: ...)` (MUST), plus a `(Migration: ...)` (SHOULD) whenever the removal affects consumers, or behavior that was persisted |
| `## RENAMED Requirements` | only the requirement's heading or name changes, not what it requires, unless the same delta also holds a `MODIFIED` block for the renamed one | the old name and the new one, both written out (MUST) |

## `openspec/config.yaml`

The reference layout of the file, with example `rules` for each phase:

```yaml
schema: spec-driven

context: |  # filled in by sdd-init from what it detected
  Tech stack: {detected}
  Architecture: {detected}
  Testing: {detected}
  Style: {detected}

rules:
  proposal:  # applied by sdd-propose
    - Give every risky change a rollback plan
  specs:  # applied by sdd-spec
    - Write scenarios as Given/When/Then
    - State obligations with the RFC 2119 words MUST, SHALL, SHOULD and MAY
  design:  # applied by sdd-design
    - Add a sequence diagram for every complex flow
    - Record each architecture decision together with its rationale
  tasks:  # applied by sdd-tasks
    - Group tasks by phase and number them hierarchically
    - Size each task so that one session can finish it
  apply:  # applied by sdd-apply
    guidelines:
      - Stay with the code patterns the project already uses
    tdd: false  # true switches on RED-GREEN-REFACTOR
    test_command: ""
  verify:
    test_command: ""
    build_command: ""
    coverage_threshold: 0
  archive:  # applied by sdd-archive
    - Merging a destructive delta needs a warning first
```

## Once a change is archived

Archiving moves the change folder to `openspec/changes/archive/YYYY-MM-DD-{change-name}/`, dated
with today's date in ISO format. What lands there is the AUDIT TRAIL: an archived change is never
deleted and never modified.
