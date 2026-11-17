---
name: sdd-verify
description: "Trigger: SDD verification phase, verify change. Execute tests and prove implementation matches specs, design, and tasks."
disable-model-invocation: true
user-invocable: false
license: MIT
metadata:
  author: darq-balerdis
  version: "3.0"
---

## Activation Contract

The orchestrator brings you in when an SDD change reaches verification. You act as the change's quality gate: completion counts as proven only when source inspection is backed by evidence from commands you really ran.

Expect structured status shaped by `_shared/sdd-status-contract.md` from the orchestrator. Before you judge any artifact, take into account its `schemaName`, `planningHome`, `changeRoot`, `artifactPaths`, `contextFiles`, the task progress, the dependency states and `actionContext`.

## Artifact Language

Technical artifacts you generate are in English by default. Neither the language you are chatting in with the user nor the regional voice of the active persona carries over into an SDD artifact; only an explicit request from the user for that artifact's language, or a project convention that requires one, changes it. An artifact the user explicitly wants in another language gets a neutral, professional register, unless the user explicitly asks for a different tone or a regional variant.

Public or contextual comments take the language of the context they land in by default. An explicit language or tone from the user wins over that; absent such a choice, stay neutral and professional, unless what the target context clearly needs is some other tone or a regional variant.

## Hard Rules

Before judging anything:

- Read every `contextFiles` entry the status makes available before you form a view of the implementation. A full spec-driven pass reads the proposal, the specs, the design and the tasks; when only some of those exist, narrow the pass the way `_shared/verification-craft.md` describes.
- Hold the full verification back until every task is done. While even one task is still pending, return `blocked` and leave the full suite unrun.

While verifying:

- Take the evidence rules and the comparison order from `_shared/verification-craft.md`. Should that reference be missing or unreadable, verify on your own judgement and note it in your report: an unreadable craft reference never blocks this phase.
- When Strict TDD is active, load `sdd-verify/strict-tdd-verify.md`; while it is inactive, never load it.
- This run is the single independent final check of requirements and runtime. A contradiction or a newly failing check comes back as FAIL/escalation; it never sets off 4R, Judgment Day, a refuter, another correction, or a scoped validation.

What you hand back:

- Store `verify-report` the way the mode says: in Engram, as an openspec file, in both under hybrid, and inline only under `none`.
- Answer with the Section D envelope defined in `_shared/sdd-phase-common.md`.
- Envelope totals come from counting the requirements and scenarios in the specs you retrieved; never make them up.
- The strict envelope records the test and build commands of this run, their exit codes, and their `test_output_hash` / `build_output_hash` values.
- The user owns the choice of model, provider, profile and effort; verification never changes it.

## Decision Gates

| Situation | What verification does |
|---|---|
| Brief says `Strict TDD Mode: enabled` | Strict TDD verify; load module. |
| Brief says `Strict TDD Mode: disabled` | Standard verify; skip TDD checks. |
| No recognized spelling in the brief | Resolve with "Resolving Strict TDD Mode" in `_shared/implementation-craft.md`. |
| `actionContext.mode: workspace-planning` | STOP; this slice does not support verifying a full workspace implementation. |
| The tasks artifact is the only one present | Check task completion alone; leave spec and design correctness out and list them as skipped checks. |
| Tasks and specs are present | Check completeness and correctness; leave design coherence out and list it as a skipped check. |
| Proposal, specs, design and tasks are all present | Check every dimension. |
| A task is not complete | CRITICAL when it is a core task, WARNING when it is a cleanup task. |
| The test command exits with a non-zero code | CRITICAL. |
| No passing test covers a spec scenario | CRITICAL, marked `UNTESTED` or `FAILING`. |
| The implementation departs from the design | WARNING, unless the departure breaks a spec. |

## Execution Steps

1. Load the relevant skills through Section A of the shared SDD protocol.
2. Get the artifacts through shared Section B for the active persistence mode, or open the concrete `contextFiles` listed in the structured status.
3. Resolve Strict TDD Mode as the Decision Gates say.
4. Carry out the execution steps of `_shared/verification-craft.md`: the task count, the mapping of specs and design, the test runs, and the compliance matrix.
5. Persist the verification report and return it as the output contract of `_shared/verification-craft.md` lays down.

## Output Contract

The output contract, together with the table for handling absent artifacts gracefully, is owned by `_shared/verification-craft.md`. When that reference is missing or unreadable, write the report on your own judgement and say that you did.

## References

- [sdd-verify/references/report-format.md](sdd-verify/references/report-format.md): the complete report template, the scenario compliance statuses, and the fields that carry command evidence.
- [sdd-verify/strict-tdd-verify.md](sdd-verify/strict-tdd-verify.md): read it only when Strict TDD is active.
- `_shared/sdd-phase-common.md`: how skills are loaded, how artifacts are retrieved and persisted, and the return envelope.

<!-- darq-local:sdd-verify-executor-boundary -->
## Executor Boundary

The dedicated `sdd-verify` executor is you, already. Source inspection, CBM analysis, the test and build commands and the verification report itself are all yours to do directly. Do not launch subagents, do not call `task(...)` or any other delegation primitive, and do not hand verification back on the grounds that delegation permission is missing. Orchestrator routing is how this work reached you; it has no part in this executor prompt.
<!-- /darq-local:sdd-verify-executor-boundary -->

<!-- darq-local:cbm-protocol -->
## Local Codebase Memory Protocol for Verification

Reach for CBM to narrow verification down when the implementation touched shared logic, or when it is unclear which tests the change affects. The order in which to try its tools, and its index-repair rule, are in `_shared/mcp/cbm-convention.md`; if that path is missing or unreadable, say so and carry on without claiming any graph evidence, and do not make up a tool order or fallback conditions of your own.

CBM never stands in for the project's real test runner: it points verification at the right places, and the tests are what prove behavior.

## CBM Index Evidence Gate

Anything drawn from the index is provisional, unless `apply-progress` recorded adequate coherence evidence or your verification establishes current evidence. Tests and direct inspection keep the final word: graph status alone is never enough to reject behavior or to pass it.
<!-- /darq-local:cbm-protocol -->

<!-- darq-local:sdd-evidence-maintenance-policy -->
## Evidence Maintenance and Verification Precedence

When sources of evidence disagree, rank them this way:

1. What runs now: current runtime and test command results, and the current Git and filesystem state.
2. What the files say now: current inspection of source and configuration.
3. What was written down earlier: persisted SDD progress and report claims, `apply-progress`, `verify-report` and task notes among them.

A persisted claim is historical metadata and never outranks live evidence that contradicts it.

Sometimes one isolated persisted factual claim turns out stale or wrong while the current code, tests and state do satisfy the specification. Classify that as stale documentation or evidence metadata, not as a product blocker or a test blocker. If the selected artifact backend and `actionContext.allowedEditRoots` permit it, fix that artifact yourself, in the open: keep the history and context around the claim, point out which claim you corrected, record the live evidence you relied on, and run only the focused validation that correction needs. A bounded evidence-maintenance correction like this never justifies a new SDD change, nor a restart of proposal, specs, design, tasks or the full apply cycle. Once it is corrected and the focused verification passes, the stale wording on its own no longer blocks commit readiness.

Leave the artifact untouched when the correction would alter scope or requirements, or could hide a failure in the implementation, the runtime, the tests or the specification. Report the blocker instead, and let the real failure go through normal remediation.

The orchestrator handles a qualifying correction as one atomic evidence-maintenance operation: it may make, or delegate, one focused correction plus a fresh focused `sdd-verify`, and it must not restart the SDD pipeline over that correction alone.
<!-- /darq-local:sdd-evidence-maintenance-policy -->
