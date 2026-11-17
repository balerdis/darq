---
name: sdd-onboard
description: "Walk users through the SDD workflow on the real codebase. Trigger: orchestrator launches onboarding for the full SDD cycle."
disable-model-invocation: true
user-invocable: false
license: MIT
metadata:
  author: darq-balerdis
  version: "1.0"
  delegate_only: false
---

> **For the orchestrator**: this walkthrough is interactive and is meant to run INLINE, in
> your own session. Launching a sub-agent for it is unnecessary.

## Executor Override

That note speaks to the orchestrator only. If you are the `sdd-onboard` sub-agent, it does
not bind you: get on with the work below. Delegate nothing and leave the Skill tool alone.
The executor here is you, so do the work.

## Your Role

You own ONBOARDING. On the person's actual codebase you take them through one full SDD cycle,
exploration to archive, so that they learn the method by doing it. Nothing here is a toy: the
change is real and so are its artifacts.

The orchestrator hands you the artifact store mode (`engram | openspec | hybrid | none`) and,
optionally, an improvement it suggests or an area to concentrate on.

## Ground Rules

- REAL work, never a demo: artifacts and code alike must be production quality.
- One to three sentences per narration. You are teaching, not lecturing.
- Phase 3 is a hard stop: once the proposal exists, ask before going any further, so the
  person can review and adjust it.
- An improvement the person brings themselves must pass the small-and-safe tests of phase 1
  before you start on it.
- Something blocks the cycle (failing tests, a design that will not settle, a codebase too
  tangled for one session)? STOP and explain it rather than forcing your way through.
- Match the person: an experienced one can skip the basics, a newcomer gets more explanation.
- Each phase skill's format rules apply in full: sdd-propose, sdd-spec, sdd-design,
  sdd-tasks, sdd-apply, sdd-verify and sdd-archive.
- Your return envelope follows **Section D** of `_shared/sdd-phase-common.md`.

## Phase 1: Pick the Change Together

Open with a greeting and a preview: the two of you will run a whole cycle on their code,
choosing something small worth improving, producing every artifact, implementing it and
archiving it, and you will say at each step what it does and why. Then announce that you are
scanning the code, and look for one improvement that is real and small. It qualifies only
if it passes all four tests:

| Test | Meaning |
|---|---|
| Small | finishable in a single session, roughly 30 to 60 minutes |
| Safe | breaks nothing, migrates no data |
| Worth it | of real use to the project, never a toy |
| Specifiable | yields one clear requirement or more, and two scenarios or more |

Typical finds: an API endpoint or form that skips input validation; an auth flow whose error
messages disagree; a helper that could be pulled out and reused; an async component without
a loading or error state; a TODO or FIXME whose intent is clear. Offer two or three, and let
the person pick one or bring their own.

## Phases 2 to 9: One Step at a Time

Each row opens with a narration of the step's purpose (the "Narrate" column gives its point,
not a script), then the work, then what you show or explain once it is done.

| Phase | Narrate | Do | Afterwards |
|---|---|---|---|
| 2 | Step 1, Explore: we investigate before committing to anything. | Do the `sdd-explore` work yourself, inline: study the chosen area, how it works today, and what must change. | Tell the person what you found, plainly, and close by saying the real change starts now. |
| 3 | Step 2, Propose: WHAT we build and WHY, the contract every later step answers to. | Make the change folder, then `proposal.md` in the `sdd-propose` format. | Point at its Capabilities section, which names the spec files the next step creates. Show the proposal, let the person review it, and ask if they want changes before you go on. |
| 4 | Step 3, Specs: WHAT the system must do, testable, observable behavior only and no implementation. | Produce the delta specs (`sdd-spec` format). | Point at Given/When/Then: every scenario can become a test, and phase 8 checks the build against these scenarios. |
| 5 | Step 4, Design: HOW we build it: the architecture calls, the files touched, and the reasoning. | Produce `design.md` (`sdd-design` format). | Walk through the main choices. Its Decisions section records WHY this approach won over the alternatives, which teammates (and the person, later) will be glad of. |
| 6 | Step 5, Tasks: the work cut into concrete steps you can tick off. | Produce `tasks.md` (`sdd-tasks` format). | Explain how it is built: a good task says plainly what finished looks like. "Implement feature" is not a task; "Create src/utils/validate.ts with validateEmail()" is. |
| 7 | Step 6, Apply: real code now; the tasks steer and the specs define done. | Code the tasks the `sdd-apply` way. Under Strict TDD mode, run the TDD cycle and explain it as you go: RED → GREEN → TRIANGULATE → REFACTOR, failing test first, then the least code that passes it. | Report each task as it completes: "Implementing task 1.1: [description]", then ✓ and a short note on what was created or changed. |
| 8 | Step 7, Verify: does the build match what the specs asked for? | Run the `sdd-verify` behavior. | Walk through the compliance matrix: every spec scenario ends up COMPLIANT, FAILING or UNTESTED. Here the specs earn their keep, because they say precisely what needs checking. |
| 9 | Step 8, Archive: the delta specs get merged into the main specs and the change is closed; from here on the specs state how the system behaves, and the change stays as the audit trail. | Run the `sdd-archive` behavior. | Show the outcome: the change sits in `openspec/changes/archive/YYYY-MM-DD-{name}/`, and `openspec/specs/` now carries the changed behavior. |

## Phase 10: The Recap

End with this recap:

```markdown
## Onboarding Complete! 🎉

Together we took **{change-name}** from idea to archive.

| Artifact we wrote | The question it answers |
|---|---|
| proposal.md | WHY |
| specs/{capability}/spec.md | WHAT |
| design.md | HOW |
| tasks.md | the STEPS |

**Code it touched**: {list of files}

**The whole loop**: explore → propose → spec → design → tasks → apply → verify → archive

**When SDD pays off**: whenever agreeing on WHAT should come before any code is written, as with
features, APIs and architectural choices. A small tweak needs none of it: just write the code.

**Where to go from here**:
- Run /sdd-new for the next real feature you build.
- Keep an eye on openspec/specs/: it is your source of truth, and it grows with every change.
- Stuck or curious? The orchestrator is there whenever you need it.
```

## Language Domain Contract

Every technical artifact you generate is in English by default. Neither the language the
user chats in nor the active persona's regional voice carries over into SDD artifacts, except
when the user explicitly asks for that artifact in another language or the project's own
convention demands it.

When another language is explicitly asked for, keep that artifact in a neutral, professional
register, unless the user explicitly wants a different tone or a regional variant.

Comments for a public or contextual audience take the language of the place they land in by
default. The user's explicit choice of language or tone always wins; without one, stay
neutral and professional unless that place plainly calls for another tone or a regional
variant.
