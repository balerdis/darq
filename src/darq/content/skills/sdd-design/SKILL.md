---
name: sdd-design
description: "Create the SDD technical design and architecture approach. Trigger: orchestrator launches design for a change."
disable-model-invocation: true
user-invocable: false
license: MIT
metadata:
  author: darq-balerdis
  version: "2.0"
  delegate_only: true
---

> **ORCHESTRATOR GATE.** Whoever opens this file with the `skill()` tool is the orchestrator, and must not
> run the phase inline: halt here and launch the `sdd-design` sub-agent through the platform's delegation
> primitive (`task(...)`, sub-agent invocation, and so on). What follows is for executors only.

## For the sdd-design sub-agent

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

You own the TECHNICAL DESIGN of one change. Read its proposal and its specs, then write `design.md`, the
document that settles HOW the change gets built: the architecture decisions behind it, the way data moves
through it, which files it touches, and the technical reasoning that holds all of that together.

Two things arrive with your launch: the name of the change, and the artifact store mode, which is one of
`engram | openspec | hybrid | none`.

## Inputs and outputs per store mode

Fetching follows **Section B** of `_shared/sdd-phase-common.md`; saving follows its **Section C**. For this
phase the modes mean:

- `engram`: the proposal is required, at `sdd/{change-name}/proposal`. The spec, at `sdd/{change-name}/spec`,
  is optional: sdd-spec may be running alongside you and not have saved it yet. Your result is saved under
  `sdd/{change-name}/design`.
- `openspec`: do what `_shared/openspec-convention.md` prescribes, after reading it.
- `hybrid`: honor both conventions together: the Engram save and a `design.md` on disk. Inputs come from
  Engram first; the filesystem is the fallback.
- `none`: hand the result back and nothing more; no project file is created or changed.

## Procedure

1. **Skills.** Load them as **Section A** of `_shared/sdd-phase-common.md` describes.
2. **Code before design.** Before deciding anything, open the code this change will affect and learn from
   the source itself where its entry points are and how its modules are arranged, which conventions and
   patterns it already follows, what it depends on and which interfaces are involved, and what test
   infrastructure exists, if any does.
3. **Threat matrix check.** Ask whether the design changes routing, shell commands or subprocesses, VCS/PR
   automation, the classification of files as executable, or process integration. If it changes any of
   them, read `sdd-design/references/threat-matrix.md` and bring its matrix into the design: each row gets
   `Applicable` or an explicit `N/A` with its reason, and each applicable case gets its expected
   safe/failure behavior and the RED tests planned for it. If none of these boundaries is present, note the matrix as
   not applicable and invent no tasks on its account.
4. **Write the design** as "The design.md template" below lays it out, following "Design rules". Under
   `openspec` or `hybrid` that is the file `openspec/changes/{change-name}/design.md`, placed in the change
   directory beside `proposal.md` and `specs/`. Under `engram` or `none`, create neither an
   `openspec/` directory nor any file inside one; the design waits in memory for step 5.
5. **Persist. This step is mandatory and is never skipped.** Apply **Section C** of
   `_shared/sdd-phase-common.md` with artifact `design`, topic_key `sdd/{change-name}/design`, and type
   `architecture`.
6. **Report** to the orchestrator with the summary in the next section, inside the return envelope that
   **Section D** of `_shared/sdd-phase-common.md` defines.

## What you send back

```markdown
## Design Created

**Change**: {change-name}
**Location**: `openspec/changes/{change-name}/design.md` (openspec/hybrid) | Engram `sdd/{change-name}/design` (engram) | inline (none)

### Summary
- **Approach**: {a single line naming the technical approach}
- **Key Decisions**: {how many decisions the design records}
- **Files Affected**: {counts of files created, modified and deleted}
- **Testing Strategy**: {the coverage planned at the unit, integration and e2e levels}

### Open Questions
{every question still open, or "None"}

### Next Step
The tasks phase (sdd-tasks) can start.
```

## Design rules

Ground everything in the code:
- Read the existing code before any design work, ALWAYS; a design built on guesses is not acceptable.
- What the project really does, in its own conventions and patterns, outranks generic best practice. When
  the code follows a pattern you would not have chosen, say so, and still FOLLOW it, unless the change
  specifically addresses that pattern.
- Name concrete file paths; describing a file in the abstract does not count.

Decide with reasons:
- Every decision MUST carry its rationale, the "why".
- An open question that BLOCKS the design gets stated plainly; never guess your way past it.
- Whatever `rules.design` says in `openspec/config.yaml` applies here.

Keep it lean:
- The design artifact MUST stay under 800 words. Architecture decisions go in tables with the columns
  option | tradeoff | decision; code snippets appear only for patterns that are not obvious.
- ASCII diagrams stay simple: being clear matters more than being pretty.

Carry threats forward:
- An applicable threat-matrix row is a design requirement. It MUST reach the tasks and the RED tests
  without changes. A row marked with an explicit `N/A` needs no task.

## Reference files

- [sdd-design/references/threat-matrix.md](sdd-design/references/threat-matrix.md): load it only when the
  design crosses one of the boundaries step 3 of the procedure lists.

## The design.md template

```markdown
# Design: {Change Title}

## Technical Approach

{A few sentences on the overall technical strategy: how it delivers the approach the proposal picked, and
which specs it answers to.}

## Architecture Decisions

### Decision: {Decision Title}

**Choice**: {what was adopted}
**Alternatives considered**: {what was turned down}
**Rationale**: {what makes the adopted option better}

### Decision: {Decision Title}

**Choice**: {what was adopted}
**Alternatives considered**: {what was turned down}
**Rationale**: {what makes the adopted option better}

## Data Flow

{The route data travels across the system in this change, with an ASCII diagram wherever one helps.}

    Client ──→ API ──→ Service
                          └──→ Repository ──→ Database

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/area/new_part.ext` | Create | {the job the new file does} |
| `src/area/current_part.ext` | Modify | {the change made to it, and its reason} |
| `src/area/old_part.ext` | Delete | {the reason it is removed} |

## Interfaces / Contracts

{Any interface, API contract, type definition or data structure the change introduces, each in a code block
in whatever language the project is written in.}

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | {target} | {technique} |
| Integration | {target} | {technique} |
| E2E | {target} | {technique} |

## Threat Matrix

{When routing, shell or process integration is involved: the applicability matrix of `sdd-design/references/threat-matrix.md`, filled in. When none is:
`N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.`}

## Migration / Rollout

{How any data migration, feature flag or phased rollout will be handled; if the change needs none of them,
write "No migration required."}

## Open Questions

- [ ] {a technical point nobody has settled yet}
- [ ] {a choice that is waiting on the team}
```

<!-- darq-local:cbm-protocol -->
## Local Codebase Memory Protocol for Design

Use CBM to validate design decisions when the change touches non-trivial coupling, shared abstractions, public APIs, routes, persistence flows, or cross-module behavior. Follow the tool priority order and the index-repair rule in `_shared/mcp/cbm-convention.md`. If that path is missing or unreadable, say so and proceed without claiming graph evidence; do not invent your own tool order or fallback conditions.

Skip CBM for isolated UI/copy/docs/config-only design where graph relationships do not matter.
<!-- /darq-local:cbm-protocol -->
