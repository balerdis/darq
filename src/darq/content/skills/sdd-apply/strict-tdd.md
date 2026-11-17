# Strict TDD in the Apply Phase

> **Scope: this module is in play ONLY while Strict TDD Mode is enabled AND a test runner is
> available.** The orchestrator checked both before handing you this file, so follow every
> instruction in it.

## Rules (Strict TDD specific)

The short version comes first; the sections after it spell out each rule.

- NEVER write production code before its test has been written AND run and seen to fail. This is the ONE rule with no exceptions, and a test that was only written has not been run.
- NEVER skip the GREEN execution gate: you MUST run the tests and confirm they pass.
- NEVER skip triangulation when the spec defines several scenarios; a hardcoded Fake It has to be forced out.
- NEVER write trivial assertions (the "Banned Shapes" below); they are WORSE than no test.
- ALWAYS check that every assertion CALLS production code and asserts a SPECIFIC expected value.
- ALWAYS run the Safety Net before modifying files that already exist, to protect what already works.
- ALWAYS report the TDD Cycle Evidence table; the verify phase checks it.
- When a test runner execution fails for infrastructure reasons, not because of test failures, report it as "Blocked" and continue with the next task.
- Prefer pure functions, but do not force them where they do not fit (React components with state, for example).
- For refactoring tasks, ALWAYS write approval tests before touching the code.
- During the cycle run ONLY the relevant test file, never the full suite.

## Evidence in the Return Summary

With Strict TDD Mode active, your return summary MUST contain the section below. The same table is
also saved once as this batch's evidence record (`sdd/{change-name}/apply-evidence/{n}`; see Step 6
in `sdd-apply/SKILL.md`), and apply-progress keeps only the ledger line that points at it.

```markdown
### TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1 | `tests/test_shipping.py` | Unit | ✅ 7/7 | `pytest tests/test_shipping.py::test_express_surcharge` → `AttributeError: module 'shipping' has no attribute 'shipping_cost'` | ✅ Passed | ✅ 3 cases | ✅ Clean |
| 2.2 | `tests/test_shipping.py` | Unit | ✅ 9/9 | `pytest tests/test_shipping.py::test_free_over_threshold` → `AssertionError: assert 12.0 == 0` (existing function, new branch) | ✅ Passed | ✅ 2 cases | ➖ None needed |
| 2.3 | `src/cart/summary.test.tsx` | Integration | N/A (new) | `vitest run src/cart/summary.test.tsx -t "lists every line item"` → `ReferenceError: CartSummary is not defined` | ✅ Passed | ➖ Single | ✅ Clean |

### Test Summary
- **Total tests written**: {count}
- **Total tests passing**: {count}
- **Layers used**: Unit ({count}), Integration ({count}), E2E ({count})
- **Approval tests** (refactoring): {count}, or "None: no task refactored existing code"
- **Pure functions created**: {count}
```

What each column holds:

- **Safety Net**: the tests that already existed, run before you modified the file; "N/A (new)" for a file you created.
- **RED**: the command you ran and the failure it produced, at a point when no production code for this task existed yet. Write it as `{command} → {failure}` and quote the actual error or failed assertion, e.g. `pytest test.py::test_x` → `AttributeError: ...`. A bare `1 failed` is weak evidence; the specific message is the part a fabricated cell cannot cheaply invent. Never "✅ Written" alone: that records only that a file exists, not that it ran, let alone that it ran first.
- **GREEN**: the tests, executed and passing after the minimal implementation; the cell must show that execution result.
- **TRIANGULATE**: the extra cases added to force real logic; "➖ Single" when the spec has only one scenario.
- **REFACTOR**: the improvement made with the tests still passing; "➖ None needed" when the code was already clean.

## Tests as the Design Tool

Here TDD is not a testing activity; it is **software design driven by tests**. First a test states
what the code SHOULD do, and only then does the minimum code that makes the statement true get
written. The tests are what design the API, the contracts and the behavior; the code falls out of
them as a side effect.

Three laws hold the whole time:

1. **No production code** until a failing test exists for it.
2. **No more test** than it takes to fail.
3. **No more code** than it takes to make that test pass.

## The Per-Task Cycle

Every task assigned to you goes through this cycle, strictly. Most step names (SAFETY NET, RED,
GREEN, TRIANGULATE, REFACTOR) are also columns of the evidence table above.

```
EACH ASSIGNED TASK
├── 0. SAFETY NET (skip it unless you are modifying files that already exist)
│   ├── Run the tests that already cover the files you are about to modify
│   ├── Write down the baseline as "{N} tests passing"; later it shows that
│   │   nothing which worked before got broken
│   └── Any of them FAIL → STOP and report it as "pre-existing failure";
│       do NOT fix a pre-existing failure, report it to the orchestrator
├── 1. UNDERSTAND the task before touching it
│   ├── The task description
│   ├── The spec scenarios it touches: they ARE the acceptance criteria
│   ├── The design decisions: they CONSTRAIN how you may build it
│   ├── Existing code and tests: match their patterns and style
│   └── The test layer (see "Picking the Test Layer")
├── 2. RED: a failing test FIRST, then RUN it and OBSERVE how it fails
│   ├── Write test(s) for the behavior the spec expects, leaning toward pure
│   │   functions, which have no side effects and are easy to test
│   ├── The test SHOULD reference production code that does NOT exist yet;
│   │   that makes a failure likely, and likely is not the same as observed
│   ├── RUN the test now, before writing any production code for this task,
│   │   and record the exact command and the failure it printed, verbatim
│   ├── The failure MUST come from the behavior this test describes
│   ├── A blanket "module/method does not exist" failure IS a legitimate RED
│   │   for the task that FIRST introduces that method or module. It does
│   │   NOT individually prove the other scenarios behind it: one shared
│   │   error can hide several untested cases, and each of them still needs
│   │   its own observed failure once the symbol it depends on exists
│   ├── A failure caused by setup or environment (a misconfigured mock, an
│   │   unrelated import error) is not RED; it is a broken fixture. Repair it
│   │   and re-run until the test fails for the reason it is actually about
│   ├── Production code/function already there? Test the NEW behavior it does
│   │   not implement yet, run that test, and confirm IT fails on its own
│   │   assertion
│   └── GATE: GREEN waits until the failure has been RUN and OBSERVED; a test
│       that was written but never executed is not RED
├── 3. GREEN: the MINIMUM code that passes
│   ├── Implement ONLY what the failing test asks for
│   ├── Fake It is VALID at this point; a hardcoded return value is fine
│   ├── EXECUTE the tests; they must PASS
│   │   ├── ✅ They pass → go on to TRIANGULATE or REFACTOR
│   │   └── ❌ They fail → change the implementation, NOT the test
│   └── GATE: nothing moves on until an actual run has confirmed GREEN
├── 4. TRIANGULATE: MANDATORY for most tasks
│   ├── REQUIRED by default; skipping it takes a compelling reason
│   ├── Add another test case whose inputs and expected outputs are DIFFERENT
│   ├── EXECUTE; once the Fake It stops working because a hardcoded value no
│   │   longer fits, generalize it into real logic (that is the whole point)
│   ├── One pass is: write a test → run it → fix the implementation; keep
│   │   making passes until EVERY spec scenario of this task is covered
│   ├── MINIMUM two test cases per behavior, a happy path plus one edge case:
│   │   ├── one whose data yields a NON-EMPTY, NON-TRIVIAL result
│   │   └── one whose data drives a DIFFERENT code path
│   ├── A GREEN that passes trivially is NOT a real GREEN, for example when
│   │   ├── the component or element under test was never rendered
│   │   ├── the loop holding the assertion ran 0 times
│   │   └── the setup never reaches the code path in question
│   │   A real GREEN means production code RAN and produced the expected output
│   ├── Leaving triangulation out is allowed ONLY when ALL of these are true:
│   │   ├── the task is purely structural (a config file, a constant
│   │   │   definition, a type export)
│   │   ├── it has literally ONE possible output: no branching, no logic
│   │   └── the evidence table says so explicitly, as
│   │       "Triangulation skipped: {reason}"
│   └── GATE: REFACTOR waits until every spec scenario of this task has a test
├── 5. REFACTOR: better code, same behavior
│   ├── Pull magic numbers out into constants
│   ├── Pull logic out into functions to cut cyclomatic complexity
│   ├── Sharpen names and remove duplication
│   ├── Move toward pure functions where that is feasible
│   ├── Boy Scout Rule: the code ends up cleaner than you found it
│   ├── EXECUTE the tests after EACH refactoring step; they must STILL PASS
│   │   ├── ✅ Still passing → the step was safe, carry on
│   │   └── ❌ Failing → REVERT that one step and try a smaller one
│   └── GATE: green after EVERY refactoring change
├── 6. Tick the task complete [x]
└── 7. Write down any deviation or issue you ran into
```

## Picking the Test Layer

Each task's layer comes from the cached testing capabilities of the selected artifact store: the
Engram key `sdd/{project}/testing-capabilities`, or the `testing:` section of
`openspec/config.yaml`. What the task does decides which layer fits:

| What the task covers | Layer |
|----------------------|-------|
| Pure logic: a utility function, a calculation, a data transformation | Unit, available whenever a test runner exists |
| Rendering a component, user interaction, state changes | Integration when its tools are available; otherwise a unit test with mocks (degrade gracefully) |
| A flow across several components, API interaction, context/provider behavior | Integration when its tools are available; otherwise a unit test with mocks |
| A critical business flow, a full user journey, navigation across pages | E2E when its tools are available; otherwise integration if that is available; otherwise unit (degrade gracefully) |
| Anything else | Unit, the fallback that is always there |

**Key rule**: go for the HIGHEST available layer that fits the task. A layer being unavailable is
NEVER a reason to skip a task; drop to the next layer that is available instead.

## Running Tests

The test command comes from the cached testing capabilities, where `test_runner.command` is the
fastest source because it was already detected. `rules.apply.test_command` in
`openspec/config.yaml` acts as an override. As a fallback, detect the command from `package.json`,
`pyproject.toml` or `go.mod`.

While cycling, run ONLY the test file that matters, never the whole suite: that keeps every loop
FAST, and full-suite runs belong to sdd-verify, not to this phase. Typical shapes, adapted to
whatever the runner's CLI expects:

- JS/TS: `{runner} {test-file-path}`, such as `pnpm vitest run src/utils/tax.test.ts`
- Python: `pytest {test-file-path}`
- Go: `go test ./{package}/... -run {TestName}`

## Assertion Quality (MANDATORY)

Every assertion must check REAL behavior. A test that goes green without exercising production
logic is worse than having no test at all, because what it buys is false confidence.

### What Makes an Assertion Real

An assertion counts only when ALL three of these are true of it:

1. **It calls production code**: a function, method or component of the implementation runs in the
   test.
2. **It asserts a specific output**: the result is compared with a concrete expected value taken
   from the spec.
3. **It would FAIL if the production code were wrong**: alter the implementation logic and THIS
   test breaks.

Examples that qualify, because production code decides each result:

- `expect(shippingCost(5, true)).toBe(30)`: a real input giving a real output
- `expect(screen.getByText('Welcome back, Ana')).toBeInTheDocument()`: text rendered from data
- `assert findings[0].severity == "HIGH"`: a specific finding produced by running the check
- `assert response.status_code == 404`: the endpoint's real HTTP response
- `expect(rows).toHaveLength(4)`: valid because exactly four rows were set up

### Behavior, Not Implementation Details

Assert what the user can see, not how the code happens to be built:

```
// ❌ tied to styling: breaks on any style refactor
expect(badge.className).toContain("bg-red-500");
expect(badge.className).toContain("rounded-sm");
expect(badge.style.fontWeight).toBe("700");

// ❌ tied to internals: breaks whenever the implementation changes
expect(fetchMock.mock.calls.length).toBe(2);   // why 2? brittle
expect(form.state.submitting).toBe(false);     // internal state, not behavior

// ✅ behavioral: survives refactors and tests what users see
expect(screen.getByText("Card declined")).toBeInTheDocument();
expect(screen.getByRole("alert")).toHaveTextContent("Retry");
expect(screen.getByRole("button", { name: "Pay" })).toBeDisabled();
```

**CSS class assertions are NEVER valid test assertions.** When visual styling needs checking:

1. test the **semantic outcome** instead: the element has `role="alert"`, the text is visible, the
   button is disabled;
2. OR use a visual regression tool or an E2E screenshot comparison;
3. NEVER assert particular Tailwind/CSS class names, which are implementation details.

### Mocks

**Needing more mocks than assertions means you are testing at the WRONG level.** Count them per
test file:

- up to 3 mocks: ✅ healthy, a focused test;
- 4 to 6 mocks: ⚠️ consider extracting the logic into a pure function;
- 7 or more: ❌ STOP, this is the wrong layer. Either extract the logic under test into a PURE
  FUNCTION and test it with no mocks, OR move the test to the integration/E2E layer, where the real
  dependencies exist. NEVER write 10+ mocks to check a one-line transformation.

**Extract-Before-Mock Rule**: when the behavior to test is a data transformation, a mapping, a
filter or conditional logic (a `MUTED → FAIL` status conversion, for instance), EXTRACT it into a
pure function FIRST and test that function directly; no mocks are needed. The same idea in code:

```
// ❌ BAD: fifteen mocks to check one line of mapping
vi.mock("react-router-dom", ...);
vi.mock("@/hooks/useSession", ...);
vi.mock("@/ui/Badge", ...);
// ...twelve more...
render(<TicketRow ticket={archivedTicket} />);
expect(screen.getByText("CLOSED")).toBeInTheDocument();

// ✅ GOOD: the mapping is a pure function, tested with ZERO mocks
export function ticketLabel(state: string, archived: boolean): string {
  return archived ? "CLOSED" : state;
}
expect(ticketLabel("OPEN", true)).toBe("CLOSED");
expect(ticketLabel("OPEN", false)).toBe("OPEN");
```

### Smoke Tests

Rendering a component without asserting anything about its output is NOT a valid test:

```
// ❌ smoke only: shows the component rendered, nothing about its behavior
render(<OrderPanel order={sampleOrder} />);
expect(screen.getByTestId("panel")).toBeInTheDocument();

// ✅ behavioral: shows what the component DOES with the data
render(<OrderPanel order={sampleOrder} />);
expect(screen.getByText("Order #1042")).toBeInTheDocument();
expect(screen.getByRole("button")).toHaveTextContent("Cancel order");
```

"Renders without crash" is a smoke test. It is NOT a unit test, NOT an integration test, and it
does NOT count toward TDD coverage. Any smoke test you do need has to come with real behavioral
assertions.

### Empty Results

`expect(result).toEqual([])` or `assert len(result) == 0` is valid ONLY when all of this holds:

1. a specific precondition was set up that SHOULD lead to an empty result (no matching records,
   say);
2. production code actually ran and filtered or processed data down to nothing;
3. a companion test with a different setup produces a NON-EMPTY result (triangulation).

If the setup cannot explain WHY the result is empty, the assertion is trivial.

### Banned Shapes (NEVER write these)

| Shape | Looks like | Why it fails, and what to do instead |
|-------|------------|--------------------------------------|
| Tautology | `expect(true).toBe(true)`, `expect(false).toBe(false)`, `expect(1).toBe(1)`, `assert True`, `assert 1 == 1` | No production code takes part, so it always passes and proves nothing. |
| Empty collection with no setup behind it | `expect(result).toEqual([])`, `expect(result).toHaveLength(0)`, `assert len(result) == 0`, `assert result == []` | Valid ONLY when you set up the conditions for an empty result; otherwise nothing shows the emptiness came from real logic, or that production code ran at all. |
| Type or existence check standing alone | `expect(result).toBeDefined()`, `expect(result).not.toBeNull()`, `expect(typeof result).toBe('object')`, `assert result is not None` | Shows that something exists, not how it behaves; assert the actual value, what the object contains, what the result IS. |
| Ghost loop | assertions inside `for (const item of items)` where `items = screen.queryAllByTestId("item")` came back as `[]` | The loop body NEVER EXECUTES, so its assertions are dead code. Assert first that the collection is non-empty, as in `expect(items).toHaveLength(3)`, or set up data so it is, and only then loop. |
| Incomplete cycle: GREEN without TRIANGULATE | testing that "search does not update until Enter" while the component that receives the search is never rendered | A GREEN that passes because the setup never exercises the code path proves nothing, and you are NOT done: you MUST triangulate with a setup that DOES exercise it, here by rendering the component and verifying the behavior. |

## Pure Functions First

Production code you write in GREEN and TRIANGULATE leans toward pure functions. Compare:

```
✅ PREFER: pure, the result depends only on the arguments
function shippingCost(weightKg: number, express: boolean): number {
  return express ? weightKg * 4 + 10 : weightKg * 2
}

❌ AVOID: impure, the result reads and changes shared state
function shippingCost(order: Order) {
  session.lastCost = order.weightKg * rates.current  // side effect
  renderTotals()                                     // side effect
  return session.lastCost
}
```

A pure function is deterministic (the same input always gives the same output), has no side
effects, and is trivially testable. TDD pushes you toward such functions on its own; go with it.

## Refactoring Existing Code: Approval Tests First

When a task REFACTORS code that already exists rather than adding new code, pin its present
behavior down before touching production code:

1. Identify the behavior that has to survive.
2. Write approval tests that capture it as it is today: call the function with known inputs and
   assert the CURRENT outputs, however ugly or wrong they are. These tests document what the code
   does NOW.
3. Run them. They must PASS, since they describe current reality.
4. Only now refactor the production code.
5. Run the approval tests again. They must STILL PASS: passing means the behavior survived, failing
   means the refactor broke something and gets reverted.
6. When the spec says the behavior should CHANGE, update the approval test to the NEW expected
   behavior, run it and see it FAIL (that is RED, the new behavior not being there yet), then
   implement the new behavior until it is GREEN.
