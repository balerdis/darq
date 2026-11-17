---
name: sdd-spec
description: "Write SDD delta specs with requirements and scenarios. Trigger: orchestrator launches spec work for a change."
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
> instruction below unexecuted; hand the phase to the dedicated `sdd-spec`
> sub-agent through the delegation primitive your platform provides (`task(...)`,
> sub-agent invocation and the like, for instance). Only EXECUTORS read on.

## For the sdd-spec sub-agent

The gate speaks to the orchestrator alone. When you are the `sdd-spec` sub-agent itself, it does not bind you: carry out the phase below yourself. Do not delegate, and do not invoke the Skill tool; executing is your job.

## What This Phase Does

Starting from the proposal, you write the change's specifications as delta specs: structured requirements, each with scenarios, that state what the change ADDS to the system's behavior and what it MODIFIES, REMOVES or RENAMES.

The orchestrator launches you with two things: the change name, and the artifact store mode, one of `engram | openspec | hybrid | none`.

## What You Hand Back

Your final answer to the orchestrator is the return envelope of **Section D** in `_shared/sdd-phase-common.md`, carrying this summary:

```markdown
## Specs Created

**Change**: {change-name}

### Specs Written
| Domain | Type | Requirements | Scenarios |
|--------|------|-------------|-----------|
| {domain} | Delta/New | {added N, modified M, removed K} | {scenario count} |

### Coverage
- Happy paths: {covered/missing}
- Edge cases: {covered/missing}
- Error states: {covered/missing}

### Next Step
Design (sdd-design) can start; if a design already exists, tasks (sdd-tasks) can.
```

## Spec Formats

A domain that already has a spec gets a delta in exactly this format:

```markdown
# Delta for {Domain}

## ADDED Requirements

### Requirement: {Requirement name}

{The requirement in words, its obligations stated with MUST, SHALL, SHOULD or MAY}

The system {MUST/SHALL/SHOULD} {one specific, checkable behavior}.

#### Scenario: {The ordinary case}

- GIVEN {the starting state}
- WHEN {what happens}
- THEN {the result that must follow}
- AND {a further result, when there is one}

#### Scenario: {A boundary or failure case}

- GIVEN {the unusual starting state}
- WHEN {what happens}
- THEN {the result that must follow}

## MODIFIED Requirements

### Requirement: {Name of the existing requirement}

{The whole requirement as it now reads, which replaces the old one completely}
(Previously: {the old requirement, summed up in one line})

#### Scenario: {An existing scenario that still holds, copied over}

- GIVEN {its starting state}
- WHEN {its trigger}
- THEN {its result}

#### Scenario: {A scenario that changed, or a new one}

- GIVEN {the starting state, as it is now}
- WHEN {what happens, as it is now}
- THEN {the result, as it is now}

## REMOVED Requirements

### Requirement: {Name of the requirement that goes}

(Reason: {why the requirement goes away})
(Migration: {what takes its place, or "None" when nothing has to migrate})

## RENAMED Requirements

### Requirement: {Current name} → {New name}

(Reason: {why the name changes})
(Migration: {what references, tests or docs must follow the new name, or "None" when nothing has to migrate})
```

A domain with no spec yet is completely new, so it gets a FULL spec, not a delta, in this format:

```markdown
# {Domain} Specification

## Purpose

{What this domain is about, in a sentence or two.}

## Requirements

### Requirement: {Requirement name}

The system {MUST/SHALL/SHOULD} {a behavior}.

#### Scenario: {Scenario name}

- GIVEN {the starting state}
- WHEN {what happens}
- THEN {the result}
```

### Writing a MODIFIED Requirement (CRITICAL: read before writing any delta)

At archive time, the block you put under `## MODIFIED Requirements` takes the place of the requirement in the main spec, whole. Whatever the block leaves out is lost, and the usual way to lose scenarios is to write only the one that changed. So build every MODIFIED block this way, in this order:

1. Find the requirement in `openspec/specs/{domain}/spec.md`.
2. Copy all of it, from its `### Requirement:` line down through EVERY one of its scenarios.
3. Paste the copy under `## MODIFIED Requirements`.
4. Edit the copy until it describes the new behavior.
5. Under the requirement text, add "(Previously: {one-line summary of what changed})".

When the change adds NEW behavior and leaves the existing behavior as it is, the requirement belongs under ADDED, not MODIFIED.

## Store Contract

Retrieval works as **Section B** of `_shared/sdd-phase-common.md` describes, and persistence as its **Section C**. Per store:

- **engram**: `sdd/{change-name}/proposal` is a required read. Specs that span several domains are concatenated into one artifact, with a header per domain, and saved as `sdd/{change-name}/spec`.
- **openspec**: read `_shared/openspec-convention.md` and work by it.
- **hybrid**: both conventions at once, so Engram receives the single concatenated artifact and the filesystem receives one file per domain.
- **none**: the result is returned and nothing else; no project file is ever created or modified.

## Procedure

**1. Load skills.** Do what **Section A** of `_shared/sdd-phase-common.md` says.

**2. Work out which domains the change touches.** Your primary contract is the **Capabilities section** of the proposal; read it before anything else:

| Proposal entry | What it becomes | Before you write it |
|---|---|---|
| listed under "New Capabilities" | a NEW full spec, `openspec/specs/<capability-name>/spec.md`, written complete rather than as a delta | nothing to read: there is no existing behavior to refer to |
| listed under "Modified Capabilities" | a DELTA spec, `openspec/changes/{change-name}/specs/<capability-name>/spec.md` | read the existing `openspec/specs/<capability-name>/spec.md`, which your delta modifies |

A proposal in the older format, without a Capabilities section, leaves you to infer the domains from its "Affected Areas". Whenever the explicit Capabilities mapping exists, it wins.

**3. Learn the current behavior.** Under openspec or hybrid, read `openspec/specs/{domain}/spec.md` when it exists: it holds CURRENT behavior, and your deltas describe CHANGES to it. Under engram, the existing specs already came from Engram through the store contract, so the filesystem is not read. Under none there are no specs to read.

**4. Write the specs** in the formats of "Spec Formats", building every MODIFIED block as "Writing a MODIFIED Requirement" says. Under openspec or hybrid, they go inside the change folder: each domain's delta spec at `openspec/changes/{change-name}/specs/{domain}/spec.md`, next to the `proposal.md` that is already there. Under engram or none, create no `openspec/` directories and no `openspec/` files; compose the spec content in memory, and step 5 persists it.

**5. Persist the artifact.** Mandatory; never skip this step. Save it per **Section C** of `_shared/sdd-phase-common.md`, as artifact `spec` with topic_key `sdd/{change-name}/spec` and type `architecture`.

**6. Report back** with the summary and envelope of "What You Hand Back".

## Writing Rules

**Which kind of spec.** Let the proposal's **Capabilities section** decide first, since it names exactly the spec files to create. Then: no spec yet for the domain means a FULL spec; specs already there mean DELTA specs, with ADDED/MODIFIED/REMOVED sections.

**Requirements.** Their strength is always expressed in RFC 2119 keywords (MUST, SHALL, SHOULD, MAY). They describe WHAT the system does and never HOW, so implementation details stay out. Not one of them goes without at least ONE scenario.

**Scenarios.** Always in Given/When/Then form, 3-5 lines at most each, and TESTABLE: an automated test should be writable from any one of them. Cover the happy path AND the edge cases, not just one of the two.

**Kinds of change.**
- New behavior that leaves existing behavior unchanged is ADDED, not MODIFIED.
- **MODIFIED always means the FULL block**: the whole requirement with all its scenarios, copied from the main spec and only then edited. A partial block loses content at archive time.
- REMOVED MUST carry its Reason; it SHOULD carry a Migration too whenever consumers, persisted behavior, docs or tests are affected.
- RENAMED MUST give the old name and the new one explicitly; it SHOULD carry Migration guidance for references, tests and docs.

**Size budget.** Under 650 words for the spec artifact, a MUST. Requirement tables are preferred over narrative descriptions.

**Project rules.** Whatever `rules.specs` says in `openspec/config.yaml` applies.

### The RFC 2119 Vocabulary

MUST and SHALL make a requirement absolute, and MUST NOT and SHALL NOT make a prohibition absolute. SHOULD marks a recommendation that a justified exception may still set aside; SHOULD NOT marks something not recommended that justification can still make acceptable. MAY marks what is optional.

## Artifact Language

Every technical artifact this phase generates is written in English, unless the user explicitly asks for that artifact in another language or the project's own convention requires one. Neither the language of your conversation with the user nor the regional voice of the active persona carries over into SDD artifacts on its own.

When another language has been explicitly requested, keep the register neutral and professional; a different tone or a regional variant needs its own explicit request from the user.

A public or contextual comment takes the language of the context it lands in. An explicit choice of language or tone by the user beats that default; without one, stay neutral and professional unless the context plainly calls for another tone or regional variant.
