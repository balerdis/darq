---
name: sdd-propose
description: "Create an SDD change proposal with intent, scope, and approach. Trigger: orchestrator launches proposal work for a change."
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
> instruction below unexecuted; hand the phase to the dedicated `sdd-propose`
> sub-agent through the delegation primitive your platform provides (`task(...)`,
> sub-agent invocation and the like, for instance). Only EXECUTORS read on.

## For the sdd-propose sub-agent

The gate speaks to the orchestrator alone. When you are the `sdd-propose` sub-agent itself, it does not bind you: carry out the phase below yourself. Do not delegate, and do not invoke the Skill tool; executing is your job.

## What This Phase Does

You turn what is known about one change into its proposal: a structured `proposal.md` that lives in the change folder. The raw material is the exploration analysis or, when there was none, the user's own description.

The orchestrator launches you with:

- the change name, `add-dark-mode` for example;
- the exploration analysis from sdd-explore, or a direct description from the user instead;
- the artifact store mode, one of `engram | openspec | hybrid | none`.

## The Proposal Document

Write `proposal.md` in this format:

```markdown
# Proposal: {Change Title}

## Intent

{The problem this change removes and why it has to happen now: name the
user need or the technical debt precisely.}

## Scope

### In Scope
- {A deliverable you can point at}
- {Another one}
- {...}

### Out of Scope
- {Something this change deliberately does not do}
- {Related work postponed to a later change}

## Capabilities

> CONTRACT with the specs phase: sdd-spec decides from this list exactly
> which spec files it creates or updates. Look through `openspec/specs/`
> before you write it.

### New Capabilities
<!-- One entry per capability that does not exist yet; each one becomes
     `openspec/specs/<name>/spec.md`. Names are kebab-case, such as
     invoice-export or rate-limits. Leave it empty when there are none. -->
- `<capability-name>`: <what the capability covers, in a few words>

### Modified Capabilities
<!-- Capabilities that already have a spec and whose REQUIREMENTS change,
     not merely their implementation: list one only when behavior changes at
     the spec level. Each one needs a delta spec. Use the names found in
     openspec/specs/. Leave it empty when there are none. -->
- `<existing-capability-name>`: <the requirement that changes>

## Approach

{How the change will be made, at the level of the overall technique. When
an exploration recommended an approach, point to it.}

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `path/to/module` | New/Modified/Removed | {what happens there} |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| {what could go wrong} | Low/Med/High | {what limits it} |

## Rollback Plan

{The concrete steps that undo the change if it misbehaves.}

## Dependencies

- {Anything outside the change it relies on, or none}

## Success Criteria

- [ ] {An observable sign the change worked}
- [ ] {A result someone can measure}
```

What the document must get right:

- **Capabilities is never skipped.** It is the contract sdd-spec works from, so look through `openspec/specs/` before you fill it in and use the capability names that already exist there.
  - Each entry under New Capabilities turns into a new full spec at `openspec/specs/<name>/spec.md`.
  - Each entry under Modified Capabilities turns into a delta spec inside the change folder.
  - When nothing changes at the spec level (a pure refactor, a config change), write "None" under both sub-sections explicitly; never leave the template placeholders standing.
- A rollback plan is mandatory in every proposal, and so are success criteria.
- Affected Areas names concrete file paths wherever it can.
- **Size budget:** the proposal artifact MUST stay under 450 words. Reach for bullet points and tables before prose, and let headers organize rather than explain. A proposal is a tool to think with, not a novel; keep it CONCISE.

## What You Hand Back

Your final answer to the orchestrator is the return envelope of **Section D** in `_shared/sdd-phase-common.md`, carrying this summary:

```markdown
## Proposal Created

**Change**: {change-name}
**Location**: openspec/hybrid → `openspec/changes/{change-name}/proposal.md` | engram → Engram `sdd/{change-name}/proposal` | none → inline

### Summary
- **Intent**: {the intent, in one line}
- **Scope**: {N deliverables included, M deferred}
- **Approach**: {the approach, in one line}
- **Risk Level**: {Low/Medium/High}

### Next Step
The specs phase (sdd-spec) or the design phase (sdd-design) can start.
```

## Shaping Questions in Interactive Mode

When SDD runs in interactive mode, whether the proposal is "clear enough" is not something the executor settles on its own in silence. Before you finalize the proposal, offer the user a round of proposal questions, and say what the round is for: a better PRD/proposal, through the business rules, implications, impact, edge cases and product tradeoffs the answers bring to light. The user may answer, skip, correct how you framed the change, or ask for a second round.

The questions are about understanding the business, the product and the PRD, never about harness mechanics. Draw on the smallest subset of these areas that is still useful:

| Area | What the answers should reveal |
|---|---|
| Business problem | the pain, opportunity, user confusion or operational cost that makes the change worth doing now |
| Target users and situations | who is affected, in which workflow, at what moment, and how urgently |
| Business rules | policies, permissions, thresholds, lifecycle rules, compliance or security expectations, and domain invariants the proposal has to respect |
| Product outcome | what should feel, work or become possible once the change lands |
| Current-state gap | what is wrong, inconsistent, missing, ad hoc or hard to explain today |
| Implications and impact | the teams, workflows, data, UX expectations, support burden or operational processes the change may touch |
| Edge cases | failures, slow paths, empty states, partial data, permissions, migration states, unusual customers, and user needs that conflict |
| Decision gaps | the product unknowns that would leave the proposal ambiguous, risky or easy to overbuild |
| Scope boundaries and non-goals | what the first product slice holds, what is later refinement, and what must stay unchanged even though it is related |
| Business risk or tradeoff | the downside that matters most if the proposal picks the wrong direction |

How a round runs:

- Aim for 3–5 concrete product questions per round.
- Once the first answers are in, sum up the proposal assumptions they lead to and ask whether the user wants any of them corrected or a second round run.
- Test commands, PR shape, the changed-line budget and every other harness decision stay out of the questions, unless the user explicitly asks to discuss delivery.
- If you cannot put the questions to the user directly, add a `## Proposal question round` section to the proposal result, holding the questions you would ask and the assumptions the user still needs to review.

## Store Contract

Retrieval works as **Section B** of `_shared/sdd-phase-common.md` describes, and persistence as its **Section C**. Per store:

- **engram**: two optional reads, `sdd/{change-name}/explore` and `sdd-init/{project}`; the artifact is saved as `sdd/{change-name}/proposal`.
- **openspec**: read `_shared/openspec-convention.md` and work by it.
- **hybrid**: both conventions at once, so the proposal is persisted to Engram and also written to the filesystem. Dependencies come from Engram first, with the filesystem as the fallback.
- **none**: the result is returned and nothing else; no project file is ever created or modified.

Creating `openspec/` is never forced on a project: it happens only when the user asked for file-based persistence or the mode is `hybrid`.

## Procedure

**1. Shape the proposal.** In interactive mode, run the question round of "Shaping Questions in Interactive Mode".

**2. Load skills.** Do what **Section A** of `_shared/sdd-phase-common.md` says.

**3. Prepare the change folder.** Under openspec or hybrid, create `openspec/changes/{change-name}/` with `proposal.md` inside it. Under engram or none, no `openspec/` directory is created at all; skip this step.

**4. Learn the current behavior.** Under openspec or hybrid, read whatever specs in `openspec/specs/` are relevant, to see which current behavior this change might affect. Under engram, that context already came from Engram through the store contract, so the filesystem is not read. Under none there are no specs to read.

**5. Write the proposal** in the format of "The Proposal Document". If the change folder already holds a proposal, READ it first and UPDATE it rather than starting over. In `openspec` mode the `proposal.md` file is always created.

**6. Persist the artifact.** Mandatory; never skip this step. Save it per **Section C** of `_shared/sdd-phase-common.md`, as artifact `proposal` with topic_key `sdd/{change-name}/proposal` and type `architecture`.

**7. Report back** with the summary and envelope of "What You Hand Back".

Throughout, whatever `rules.proposal` says in `openspec/config.yaml` applies.

## Artifact Language

Every technical artifact this phase generates is written in English, unless the user explicitly asks for that artifact in another language or the project's own convention requires one. Neither the language of your conversation with the user nor the regional voice of the active persona carries over into SDD artifacts on its own.

When another language has been explicitly requested, keep the register neutral and professional; a different tone or a regional variant needs its own explicit request from the user.

A public or contextual comment takes the language of the context it lands in. An explicit choice of language or tone by the user beats that default; without one, stay neutral and professional unless the context plainly calls for another tone or regional variant.
