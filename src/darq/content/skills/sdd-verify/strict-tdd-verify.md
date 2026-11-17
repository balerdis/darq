# Strict TDD Verification Module

> **Loaded ONLY when Strict TDD Mode is enabled AND a test runner is available.**
> The orchestrator checked both conditions before handing you this file, so every instruction below applies.

## What Changes Under Strict TDD

Standard verification asks whether the code works. Under Strict TDD Mode it also asks whether the code was built the right way, which means whether TDD was really followed. Apply reports its own TDD evidence; your job is to test that evidence against what is actually there.

## Step 5a: TDD Compliance Check, Including the Assertion Quality Audit

Open the `apply-progress` artifact and establish whether TDD really was followed.

### Where the Evidence Lives

Judge every place below that holds evidence:

- **A ledger.** If it has a "## TDD Evidence Ledger": retrieve EVERY listed record (mem_get_observation by the recorded id under engram, the listed file under openspec), and judge each task on ALL of its rows from all of those records, taken in ledger order. A ledger entry whose record cannot be retrieved is CRITICAL: "evidence record unavailable: {key}". That is a finding of its own, a different finding from "RED has no command", and it is never reworded as that one. No override, no waiver.
- **Legacy tables.** A change started before the ledger existed can carry "TDD Cycle Evidence" tables inside apply-progress; judge those as well. With BOTH legacy tables and a ledger, judge the legacy tables AND every ledger record.
- **Neither.** If NO ledger and NO "TDD Cycle Evidence" table turns up anywhere, that is CRITICAL: the apply phase reported no TDD evidence, so Strict TDD was enabled and apply did not follow the protocol.

A correction row or a re-opened row supersedes the earlier rows for that task ONLY if it carries its own RED command and observed failure. Lacking either, the earlier rows still stand, and the task is judged on all of them together. Every row goes through the column checks below, but only the task's effective latest row (the superseding one, when there is one) is cross-checked against the current test run.

### Checking Each Task Row

```text
Every task row
├── RED column: the cell has to name the command that was run and the failure
│   it produced; a fixed string is no evidence. A bare "✅ Written" is rejected:
│   it says a test file exists, never that the test ran.
│   ├── Confirm the test file EXISTS. Necessary, but not sufficient: a file
│   │   present today cannot show the test ran before the code, only that it
│   │   exists now.
│   ├── Confirm the recorded failure is internally consistent: the assertion or
│   │   error it names should match what the test file checks, and one shared
│   │   "module/method does not exist" failure reused for several scenarios
│   │   does not cover each of them individually.
│   ├── Mind the limit: this check can confirm that an observation was recorded
│   │   and hangs together, but it cannot reconstruct afterwards whether the
│   │   test ran before the code was written. Only RED time knows that order,
│   │   which is why the observation has to be captured then, not demanded here.
│   └── CRITICAL when the test file does not exist, when the cell is
│       "✅ Written" (or the like) with no command and no observed failure, or
│       when the recorded failure does not fit the test.
├── GREEN column: the cell has to read "✅ Passed". Hold it against the Step 5b
│   test execution results: the listed test file has to PASS when you run it.
│   CRITICAL if it fails now (was it ever really green?).
├── TRIANGULATE column: for "✅ N cases", confirm the test file holds N test
│   cases; for "➖ Single", confirm the spec truly has only one scenario for
│   this task. WARNING when the spec has several scenarios but only 1 test case.
├── SAFETY NET column: "✅ N/N" means existing tests ran before the file was
│   modified (good); for "N/A (new)", confirm the file really is NEW, not modified.
│   WARNING when a modified file shows "N/A" as its safety net.
└── REFACTOR column: subjective quality, not strictly verifiable; skip the
    check and trust the report.
```

Close the step with the line "{N}/{total} tasks have complete TDD evidence".

## Step 5: Test Layer Validation

Put every test file this change created or modified into a layer:

| Layer | What it tests | Tell-tale signs |
|---|---|---|
| Unit | one function or class, in isolation | no render(), no page., no HTTP calls, dependencies mocked |
| Integration | how components interact, or user behavior | render(), screen., userEvent., testing-library imports |
| E2E | the whole system through a real browser or HTTP | page.goto(), playwright/cypress imports, a browser context |
| Unknown | cannot be classified | report it as it is |

Report the distribution as Unit, Integration and E2E, each as {N} tests across {N} files, plus a Total of {N} tests.

Then hold the layers against the capabilities. Integration or E2E tests whose tools the capabilities do not list raise the question of how they run at all; give a WARNING to tests that use tools not detected in the capabilities. Finally, note which layer covers each spec scenario, and add a SUGGESTION where critical business logic has unit tests only, but only when integration or E2E tools are available.

## Step 5d: Changed File Coverage

When the cached capabilities include a coverage tool, measure coverage for the CHANGED files in particular:

1. Run `{test_command} --coverage`, or whatever is equivalent, and parse the coverage report.
2. Keep ONLY the files this change created or modified; the list comes from the "Files Changed" table in apply-progress.
3. For each such file give its path, line coverage %, branch coverage % when there is one, and the uncovered line ranges, meaning the specific lines and not just a percentage. Rate it ✅ Excellent at ≥ 95%, ⚠️ Acceptable at ≥ 80%, and ⚠️ Low below 80%, listing the uncovered lines of a Low file.
4. Add the aggregate: the average coverage of the changed files, the total of uncovered lines across them, and how that compares with the threshold if one is configured.
5. Give a WARNING for any changed file under 80% coverage.

Without a coverage tool, report "Coverage analysis skipped: no coverage tool found". That is NOT a failure; the tool is simply not there.

## Step 5e: Quality Metrics (Only With Tools)

Take the quality tools from the cached capabilities, and run them ONLY on the changed files and ONLY if they are available:

- **Linter available**: lint the changed files alone and report its errors and warnings. Errors earn a WARNING, warnings a SUGGESTION.
- **Type checker available**: run it (usually over the whole project rather than file by file), filter the output down to the changed files, and report the type errors in them. Type errors earn a WARNING.
- **Neither available**: report "Quality metrics skipped — no tools detected".

## Step 5f: Mandatory Assertion Quality Audit

Read through ALL test files created or modified by this change, looking for assertions that are trivial or mean nothing. These patterns are banned:

| Banned pattern | How it shows up | Severity |
|---|---|---|
| Tautology | expect(true).toBe(true), assert True, expect(1).toBe(1); the test proves NOTHING | CRITICAL |
| No production code call | the assertion never reaches production code (no function call, no render, no request); the test exercises nothing | CRITICAL |
| Ghost loop | assertions inside a for/forEach over queryAll/filter results: check whether that collection could be empty, and if it could, the assertions may NEVER RUN (a loop over an empty array ALWAYS passes); flag it | CRITICAL |
| Incomplete TDD cycle | the test passes because its preconditions stop the code from running, such as behavior of a component that state keeps from ever rendering; the test must set up conditions where the code path IS exercised | CRITICAL |
| Orphan empty check | expect(result).toEqual([]) or assert len(result) == 0, UNLESS a companion test with the same setup asserts NON-EMPTY | WARNING |
| Type-only assertion on its own | toBeDefined(), not.toBeNull(), typeof checks; acceptable when the same test COMBINES them with value assertions | WARNING |
| Smoke test only | render() + toBeInTheDocument() without behavioral assertions; "renders without crash" is NOT a valid test, it must assert WHAT was rendered; smoke tests do not count toward TDD coverage | WARNING |
| Implementation-detail coupling | assertions on CSS classes, internal state or mock call counts, e.g. expect(el.className).toContain("text-xs") or expect(mock.calls.length).toBe(3); tests must assert behavior, not implementation | WARNING |
| Mock-heavy test | count vi.mock() calls against expect() calls per test file; when mocks > 2× assertions, flag "Mock-heavy test ({N} mocks, {N} assertions)", since the test sits in the wrong layer, and recommend extracting the logic into a pure function or moving the test to a higher test layer | WARNING |

Record each violation with its file, its line number, the assertion itself and why it is trivial, and give it the severity from the table.

Then look at triangulation quality by counting the distinct test cases for each behavior:

- A behavior with multiple spec scenarios but only 1 test case gets a WARNING: "Insufficient triangulation for {behavior}".
- When all of a behavior's test cases assert the SAME type of value (every one of them checking empty arrays, say), it gets a WARNING: "No variance in test expectations — all assert empty/trivial".
- A behavior is well triangulated when its tests assert DIFFERENT expected values.

Finish the audit with the line "{N} trivial assertions found across {N} files".

### Reporting the Audit

Whenever the audit finds an issue, the report carries the Assertion Quality table from the sections below, one row per finding. Rows look like these:

```markdown
| `tests/cart.test.ts` | 15 | `expect(true).toBe(true)` | Tautology, it proves nothing | CRITICAL |
| `tests/cart.test.ts` | 23 | `expect(items).toEqual([])` | Empty result with no companion non-empty test | WARNING |
| `tests/cart.test.ts` | 31 | `expect(total).toBeDefined()` | Type-only, no value is asserted | WARNING |
```

When the audit finds nothing, report "**Assertion quality**: ✅ Every assertion checks real behavior".

## Rules for This Module

- The TDD Cycle Evidence rows are the primary artifact: ALWAYS check them, in every record the apply-progress TDD Evidence Ledger lists (a record that cannot be retrieved is CRITICAL, reported as unavailable) and in any legacy table inside apply-progress.
- ALWAYS hold the test files a report names against what actually ran; never take the report on trust.
- ALWAYS run the Assertion Quality Audit (Step 5f): a trivial test is WORSE than a missing one.
- apply-progress with neither a ledger nor a TDD evidence table is CRITICAL: the protocol was not followed.
- A tautology such as expect(true).toBe(true) is CRITICAL and MUST be rewritten.
- Coverage and quality metrics inform; they do NOT block. They reach WARNING at most, never CRITICAL.
- The test layer distribution informs as well, at SUGGESTION level only.
- DO NOT fix anything: report it, and leave the decision to the orchestrator.
- When coverage or quality tools are unavailable, say so plainly and move on; a missing tool is never flagged as a failure.

## Report Sections Added Under Strict TDD

With Strict TDD Mode active, the verification report MUST carry these extra sections, in this shape:

```markdown
### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ / ❌ | {present in apply-progress, or missing} |
| All tasks have tests | ✅ / ❌ | {N}/{total} tasks come with test files |
| RED confirmed (tests exist) | ✅ / ⚠️ | {N}/{total} test files confirmed on disk |
| GREEN confirmed (tests pass) | ✅ / ❌ | {N}/{total} tests pass when run now |
| Triangulation adequate | ✅ / ⚠️ / ➖ | {N} triangulated, {N} with a single case |
| Safety Net for modified files | ✅ / ⚠️ | {N}/{total} modified files had one |

**TDD Compliance**: {N}/{total} checks pass

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | {test count} | {file count} | {tool} |
| Integration | {test count} | {file count} | {the tool, or "not installed"} |
| E2E | {test count} | {file count} | {the tool, or "not installed"} |
| **Total** | **{test count}** | **{file count}** | |

---

### Changed File Coverage
| File | Line % | Branch % | Uncovered Lines | Rating |
|------|--------|----------|-----------------|--------|
| `src/cart/total.ts` | 96% | 91% | — | ✅ Excellent |
| `src/cart/discount.ts` | 81% | 70% | L30-34, L51 | ⚠️ Acceptable |
| `src/cart/tax.ts` | 100% | 100% | — | ✅ Excellent |

**Average changed file coverage**: {N}%
{or, when no coverage tool is detected: "Coverage analysis skipped: no coverage tool found"}

---

### Assertion Quality
| File | Line | Assertion | Issue | Severity |
|------|------|-----------|-------|----------|
| {file} | {line} | {assertion} | {issue} | {severity} |

**Assertion quality**: {N} CRITICAL, {N} WARNING
{or "✅ Every assertion checks real behavior"}

---

### Quality Metrics
**Linter**: ✅ No errors / ⚠️ {N} warnings / ❌ {N} errors / ➖ Not available
**Type Checker**: ✅ No errors / ❌ {N} errors / ➖ Not available
```
