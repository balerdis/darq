# Verification Craft

## Scope

Owns how to verify an implementation well — the evidence discipline, the order of comparison, and
the report shape — independent of any change-lifecycle machinery. An agent with no SDD context can
follow this file on its own; it says nothing about artifact stores, phase envelopes, or when
verification is triggered.

## Authority

This file is the canonical owner of the verification method: what counts as evidence, the order in
which written intent is compared against the implementation, how to handle a partial set of written
artifacts, and the shape of the verification report. A calling skill states when verification runs
and what happens with its verdict; it does not restate how to verify.

## Evidence Rules

- Run the tests that matter. Reading or statically analysing the code, however carefully, is never verification on its own.
- Call a scenario compliant only after a test that covers it has passed at runtime.
- Keep the order of comparison fixed. Compare specs first, design second, task completion third.
- Fixing is not your job: every issue you find goes into the report, for the orchestrator or the user to act on.

## Distinct Execution, Not Distinct Labels

Executed evidence is only as strong as the distinctness of what executed. When a report claims N
named groups, cases, or scenarios ran, the names are a claim, not the evidence — a genuine split
changes what was selected, a renamed one only changes what was printed. Before crediting a claimed
split, resolve every claimed group to the actual command or selector it ran, never to the label
attached to it; when two or more resolve to the identical selection, credit only the first execution
and treat the rest as not executed, regardless of what their labels say.

## Execution Steps

1. Count completed and incomplete tasks. Any unchecked task blocks full verification; focused checks
   remain an implementation work-unit responsibility.
2. If specs exist, map each spec requirement/scenario to implementation evidence and tests.
3. If design exists, check design decisions against changed code. If design is missing, skip design
   coherence and record why.
4. Run test, build/type-check, and coverage commands when available. Preserve the stricter runtime
   evidence rule: source inspection alone does not prove spec scenario compliance.
5. Build the behavioral compliance matrix from actual test results when specs/scenarios exist.
6. Report the verification, naming each dimension skipped because its artifact was missing.

## Output Contract

Return `## Verification Report` with change/subject, mode, completeness table, build/tests/coverage
evidence, spec compliance matrix, correctness table, design coherence table, issues grouped as
CRITICAL/WARNING/SUGGESTION, and a final verdict of `PASS`, `PASS WITH WARNINGS`, or `FAIL`.

## Graceful Artifact Handling

What you can claim depends on which written artifacts exist:

| Artifacts present | What to verify, and the limits |
|---|---|
| Tasks alone | Only whether the tasks are objectively done; say nothing about spec correctness or design coherence. With every task checked and no runtime evidence to be had, the verdict can be `PASS WITH WARNINGS`, and it then covers task completion alone. |
| Tasks and specs | Task completeness plus the correctness of each requirement and scenario. Full scenario compliance still needs runtime test evidence: a required scenario with no covering test is CRITICAL, unless the project config explicitly allows manual verification. |
| All of them | Completeness, correctness and coherence alike. |

Whatever else is missing, and even in a report that is otherwise warnings-only, an unchecked task
stays CRITICAL.
