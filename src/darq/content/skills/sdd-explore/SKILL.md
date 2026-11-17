---
name: sdd-explore
description: "Explore SDD ideas before committing to a change. Trigger: orchestrator launches exploration or requirement clarification."
disable-model-invocation: true
user-invocable: false
license: MIT
metadata:
  author: darq-balerdis
  version: "2.0"
  delegate_only: true
---

> **ORCHESTRATOR GATE**: Loading this skill through the `skill()` tool makes you the ORCHESTRATOR,
> and the ORCHESTRATOR must STOP here: do NOT carry out these instructions inline. Hand the work to
> the dedicated `sdd-explore` sub-agent, using the delegation primitive your platform provides (e.g.,
> `task(...)`, sub-agent invocation, etc.). Only EXECUTORS use this skill.

## Executor Override

When you ARE the `sdd-explore` sub-agent rather than the orchestrator, the gate above is not addressed to you. Carry on yourself with this phase's work as written below: do NOT delegate, and do NOT call the Skill tool. As the executor, you execute.

## Your Role

EXPLORATION is your job as this sub-agent: dig into the codebase, think the problem through, weigh the possible approaches against each other, and come back with a structured analysis. By default your job ends at researching and reporting back; `exploration.md` is created only when this exploration is tied to a named change.

## Inputs

The orchestrator hands you two things: the topic or feature to explore, and the artifact store mode, which is one of `engram | openspec | hybrid | none`.

## Exploration Rules

- `exploration.md` inside the change folder, when a change name is provided, is the ONLY file you MAY create.
- The exploration rules in `_shared/exploration-craft.md` apply to you.
- Shape the return envelope by **Section D** of `_shared/sdd-phase-common.md`.

## Reading and Saving per Artifact Store

Reading context follows **Section B** of `_shared/sdd-phase-common.md`, and saving follows its **Section C**. What each mode adds:

| Mode | Reading context | Saving the artifact |
|---|---|---|
| `engram` | Look up `sdd-init/{project}` for the project context and, if useful, `sdd/` for artifacts that already exist. | Reading project context from `sdd-init/{project}` is optional; save as `sdd/{change-name}/explore`, or as `sdd/explore/{topic-slug}` when standalone. |
| `openspec` | Open `openspec/config.yaml` together with `openspec/specs/`. | Read and follow `_shared/openspec-convention.md`. |
| `hybrid` | As Section B says. | Follow BOTH conventions: persist to Engram AND write to the filesystem. |
| `none` | Rely on the context the orchestrator included in its prompt. | Return the result only. |

## Procedure

1. **Load skills.** Apply **Section A** of `_shared/sdd-phase-common.md`.
2. **Explore.** `_shared/exploration-craft.md` explains how to understand the request, investigate the codebase and compare approaches; follow it. If that reference is missing or unreadable, explore on your own judgement and say so in your report: an unreadable craft reference never blocks the phase.
3. **Persist the artifact.** For an exploration tied to a named change this step is MANDATORY, so do NOT skip it. Apply **Section C** of `_shared/sdd-phase-common.md` with artifact `explore`, topic_key `sdd/{change-name}/explore` (`sdd/explore/{topic-slug}` when standalone) and type `architecture`.
4. **Return the analysis**, as the next section describes.

## Returning the Analysis

Give the orchestrator the report shape that `_shared/exploration-craft.md` defines, wrapped in this phase's own envelope heading and closed by one extra field; when you are saving, `exploration.md` receives the same content. The envelope is owned by this phase, not by the craft reference:

```markdown
## Exploration: {topic}

### Current State
{...}

### Affected Areas
{...}

### Approaches
{...}

### Recommendation
{...}

### Risks
{...}

### Ready for Proposal
{Yes or No, plus what the orchestrator should pass on to the user}
```

What goes into each section is up to `_shared/exploration-craft.md`. This block settles only the envelope heading and the section order, and it adds `Ready for Proposal`.

## Artifact Language

Technical artifacts you generate are in English by default. Neither the language you are chatting in with the user nor the regional voice of the active persona carries over into an SDD artifact; only an explicit request from the user for that artifact's language, or a project convention that requires one, changes it. An artifact the user explicitly wants in another language gets a neutral, professional register, unless the user explicitly asks for a different tone or a regional variant.

Public or contextual comments take the language of the context they land in by default. An explicit language or tone from the user wins over that; absent such a choice, stay neutral and professional, unless what the target context clearly needs is some other tone or a regional variant.

<!-- darq-local:cbm-protocol -->
## Local Codebase Memory Protocol for Exploration

Bring in CBM when the exploration needs a semantic understanding of the code: the architecture, request and data flows, symbols, routes, dependency relationships, callers and callees, or an impact map. The priority order of its tools and its index-repair rule are in `_shared/mcp/cbm-convention.md`; if that path is missing or unreadable, say so and continue without claiming graph evidence, and do not invent a tool order or fallback conditions of your own.

Do NOT reach for CBM on tiny tasks where the relevant file is already known.
<!-- /darq-local:cbm-protocol -->
