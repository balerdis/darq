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

## Hard Rules

- Execute relevant tests; static analysis alone is never verification.
- A scenario is compliant only when a covering test passed at runtime.
- Compare specs first, design second, task completion third.
- Do not fix issues; report them for the orchestrator/user.

## Execution Steps

1. Count completed and incomplete tasks. Any unchecked task blocks full verification; focused checks
   remain an implementation work-unit responsibility.
2. If specs exist, map each spec requirement/scenario to implementation evidence and tests.
3. If design exists, check design decisions against changed code. If design is missing, skip design
   coherence and record why.
4. Run test, build/type-check, and coverage commands when available. Preserve the stricter runtime
   evidence rule: source inspection alone does not prove spec scenario compliance.
5. Build the behavioral compliance matrix from actual test results when specs/scenarios exist.
6. Report the verification, including skipped dimensions for missing artifacts.

## Output Contract

Return `## Verification Report` with change/subject, mode, completeness table, build/tests/coverage
evidence, spec compliance matrix, correctness table, design coherence table, issues grouped as
CRITICAL/WARNING/SUGGESTION, and a final verdict of `PASS`, `PASS WITH WARNINGS`, or `FAIL`.

## Graceful Artifact Handling

- **Tasks only**: verify objective task completion only. Do not claim spec correctness or design
  coherence. If all tasks are checked and no runtime evidence is available, the verdict may be
  `PASS WITH WARNINGS` for task completion only.
- **Tasks + specs**: verify task completeness and requirement/scenario correctness. Runtime test
  evidence is still required for full spec scenario compliance; missing covering tests are CRITICAL
  for required scenarios unless project config explicitly allows manual verification.
- **Full artifacts**: verify completeness, correctness, and coherence.
- **Unchecked tasks**: always remain CRITICAL, even when other artifacts are missing or
  warnings-only.
