# Report Reference for sdd-verify

## Template

~~~markdown
```yaml
schema: DARQ baseline.verify-result/v1
evidence_revision: sha256:{digest of the evidence as it stands now}
verdict: pass
blockers: 0
critical_findings: 0
requirements: {done}/{real total}
scenarios: {done}/{real total}
test_command: {the command, verbatim as run}
test_exit_code: 0
test_output_hash: sha256:{digest of the unaltered output}
build_command: {the command, verbatim as run}
build_exit_code: 0
build_output_hash: sha256:{digest of the unaltered output}
```

## Verification Report

**Change**: {name of the change}
**Version**: {version of the spec, N/A if none}
**Mode**: {Strict TDD | Standard}

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | {count} |
| Tasks complete | {count} |
| Tasks incomplete | {count} |

### Build & Tests Execution
**Build**: ✅ Passed / ❌ Failed
```text
{the build command plus the output lines that matter}
```

**Tests**: ✅ {count} passed / ❌ {count} failed / ⚠️ {count} skipped
```text
{the test command plus the detail of each failure}
```

**Coverage**: {measured}% / threshold: {required}% → ✅ Above / ⚠️ Below / ➖ Not available

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| {requirement ID} | {scenario name} | `{test file} > {test name}` | ✅ COMPLIANT |
| {another requirement ID} | {scenario name} | (no covering test found) | ❌ UNTESTED |

**Compliance summary**: {compliant count}/{scenario count} scenarios are compliant

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| {requirement name} | ✅ Implemented | {short remark} |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| {design decision} | ✅ Yes | |

### Issues Found
**CRITICAL**: {the issues, or None}
**WARNING**: {the issues, or None}
**SUGGESTION**: {the issues, or None}

### Verdict
{PASS / PASS WITH WARNINGS / FAIL}
{the reason, in one line}
~~~

With Strict TDD active, add the sections that `sdd-verify/strict-tdd-verify.md` lays out for TDD compliance, test layer distribution, changed-file coverage and quality metrics.

## Envelope and Verdict Rules

- The YAML envelope MUST be the report's first non-empty content, and each envelope field appears in it exactly once.
- Every count is taken from the specs that were actually retrieved.
- A pass needs the current test command and the current build/type-check command, each exiting with code zero and each recorded with a SHA-256 digest of its output.
- Evidence fails closed in every one of these cases: it is missing, incomplete or stale; it is invalid, unknown or contradictory; it is blocker-bearing or critical-bearing.
- Routing is never controlled by the human prose that follows the envelope.
- Choosing the model, provider, profile or effort remains the user's call.

## Scenario Statuses

| Status | When it applies |
|---|---|
| ✅ `COMPLIANT` | A test covers the scenario, and that test passed. |
| ❌ `FAILING` | A test covers the scenario, but that test failed. |
| ❌ `UNTESTED` | No test covering the scenario was found. |
| ⚠️ `PARTIAL` | The test passes, yet it covers only part of the scenario. |
