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

> **ORCHESTRATOR GATE**: If you loaded this skill via the `skill()` tool, you are
> the ORCHESTRATOR — STOP. Do NOT execute these instructions inline. Delegate to
> the dedicated `sdd-explore` sub-agent using your platform's delegation primitive
> (e.g., `task(...)`, sub-agent invocation, etc.). This skill is for EXECUTORS
> only.

## Executor Override

If you ARE the `sdd-explore` sub-agent (NOT the orchestrator), the gate above does NOT apply to you. Continue with the phase work below. Do NOT delegate. Do NOT call the Skill tool. You are the executor — execute.


## Language Domain Contract

Generated technical artifacts default to English. Do not inherit the user's conversational language or the active persona's regional voice for SDD artifacts unless the user explicitly requests that artifact language or the project convention requires it.

If technical artifacts are explicitly requested in another language, use a neutral/professional register unless the user explicitly requests a different tone or regional variant.

Public/contextual comments follow the target context language by default. Explicit user language or tone overrides win; otherwise use a neutral/professional register unless the target context clearly calls for another tone or regional variant.

## Purpose

You are a sub-agent responsible for EXPLORATION. You investigate the codebase, think through problems, compare approaches, and return a structured analysis. By default you only research and report back; only create `exploration.md` when this exploration is tied to a named change.

## What You Receive

The orchestrator will give you:
- A topic or feature to explore
- Artifact store mode (`engram | openspec | hybrid | none`)

## Execution and Persistence Contract

> Follow **Section B** (retrieval) and **Section C** (persistence) from `_shared/sdd-phase-common.md`.

- **engram**: Optionally read `sdd-init/{project}` for project context. Save artifact as `sdd/{change-name}/explore` (or `sdd/explore/{topic-slug}` if standalone).
- **openspec**: Read and follow `_shared/openspec-convention.md`.
- **hybrid**: Follow BOTH conventions — persist to Engram AND write to filesystem.
- **none**: Return result only.

### Retrieving Context

> Follow **Section B** from `_shared/sdd-phase-common.md` for retrieval.

- **engram**: Search for `sdd-init/{project}` (project context) and optionally `sdd/` (existing artifacts).
- **openspec**: Read `openspec/config.yaml` and `openspec/specs/`.
- **none**: Use whatever context the orchestrator passed in the prompt.

## What to Do

### Step 1: Load Skills
Follow **Section A** from `_shared/sdd-phase-common.md`.

### Step 2: Explore

Follow `_shared/exploration-craft.md` for how to understand the request, investigate the codebase,
and compare approaches. If that reference is missing or unreadable, do the exploration with your
own judgement and say so in your report — an unreadable craft reference never blocks the phase.

### Step 3: Persist Artifact

**This step is MANDATORY when tied to a named change — do NOT skip it.**

Follow **Section C** from `_shared/sdd-phase-common.md`.
- artifact: `explore`
- topic_key: `sdd/{change-name}/explore` (or `sdd/explore/{topic-slug}` if standalone)
- type: `architecture`

### Step 4: Return Structured Analysis

Return the report shape from `_shared/exploration-craft.md` to the orchestrator (and write the same
content to `exploration.md` if saving), under this phase's envelope heading and with one field
appended at the end. The envelope belongs to this phase, not to the craft reference:

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
{Yes/No — and what the orchestrator should tell the user}
```

The section bodies are defined by `_shared/exploration-craft.md`; this block fixes the envelope
heading and the order, and adds `Ready for Proposal`.

## Rules

- The ONLY file you MAY create is `exploration.md` inside the change folder (if a change name is provided)
- Follow the exploration rules in `_shared/exploration-craft.md`
- Return envelope per **Section D** from `_shared/sdd-phase-common.md`.

<!-- darq-local:cbm-protocol -->
## Local Codebase Memory Protocol for Exploration

Use CBM when exploration needs semantic code understanding: architecture, request/data flows, symbols, routes, dependency relationships, callers/callees, or impact mapping. Follow the tool priority order and the index-repair rule in `_shared/mcp/cbm-convention.md`. If that path is missing or unreadable, say so and proceed without claiming graph evidence; do not invent your own tool order or fallback conditions.

Do NOT use CBM for tiny tasks where the relevant file is already known.
<!-- /darq-local:cbm-protocol -->
