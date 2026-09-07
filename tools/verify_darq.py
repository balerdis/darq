#!/usr/bin/env python3
"""Behavioural verification of a *built* `darq` binary -- never of source, always of the artifact.

Every check here runs the real binary as a real subprocess, inside a throwaway `HOME` created
under a scratch directory this script owns and deletes afterward. The real environment's `$HOME`
is never read, written, or passed to the binary -- every subprocess call sets `HOME` explicitly to
the scratch home, and this module refuses to run at all if asked to use the real one.

    python3 tools/verify_darq.py
    python3 tools/verify_darq.py --binary dist/darq --keep-scratch

Checks, each falsifiable and each able to actually fail:
 1. `darq --version` names darq, never pegasus.
 2. `darq doctor --json` exits 0 and reports the *protected* wire schema `pegasus/cli-report/v1`
    -- deliberately still Pegasus's, asserted explicitly so nobody "fixes" it later.
 3. `darq install --cli opencode` exits 0 -- the real proof content-load-time invariants held.
 4. The data dir is `<home>/.local/share/darq`; `<home>/.local/share/pegasus-harness` must not exist.
 5. Brand leak scan: every installed artifact's bytes and both commands' rendered stdout are
    scanned for `pegasus` (case-insensitive; see `_LEAK_PATTERN` below for why 'harness' was
    dropped). Every hit is classified into exactly one of four outcomes, using the three named
    registers declared in `rebrand.json`:
      - silent   -- falls inside a `protected_tokens` entry (a stable wire identifier).
      - NOTE     -- falls inside an `accepted_residue` entry (cosmetic, deferred upstream debt).
      - WARNING  -- falls inside a `known_defects` entry (a known functional defect, not cosmetic,
                    reported loudly but not failed).
      - FAIL     -- none of the above. This is the only outcome that fails the check, which is
                    the whole point: a scanner that flags things nobody can ever fix trains
                    everyone to ignore it, so only a genuinely unclassified hit fails the run.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REBRAND_JSON = ROOT / "rebrand.json"
DEFAULT_BINARY = ROOT / "dist" / "darq"

# Only 'pegasus', never 'harness': every one of the 9 occurrences of 'harness' measured across a
# clean install is the ordinary English noun in technical prose ("Runtime harness command/
# scenario", "Runtime harness decisions") -- never the product name. Every branded form
# ('pegasus-harness', 'Pegasus Harness') already contains 'pegasus', so matching 'pegasus' alone
# still catches every real brand leak; keeping 'harness' in the pattern only flagged a common
# English word, and a scanner that does that is a scanner people learn to ignore.
_LEAK_PATTERN = re.compile(r"pegasus", re.IGNORECASE)

#: The four possible outcomes of classifying one leak match. Only "fail" makes the check fail.
SILENT = "silent"
NOTE = "note"
WARNING = "warning"
FAIL = "fail"


class VerificationFailure(RuntimeError):
    """One or more verification checks failed. Carries every failure found, not just the first."""


@dataclass
class Report:
    checks: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def ok(self, message: str) -> None:
        self.checks.append(f"PASS: {message}")

    def fail(self, message: str) -> None:
        self.failures.append(message)
        self.checks.append(f"FAIL: {message}")

    def note(self, message: str) -> None:
        self.notes.append(message)
        self.checks.append(f"NOTE: {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        self.checks.append(f"WARNING: {message}")

    def summary(self) -> str:
        pass_count = sum(1 for line in self.checks if line.startswith("PASS:"))
        return (
            f"{pass_count} pass, {len(self.notes)} note(s), {len(self.warnings)} warning(s), "
            f"{len(self.failures)} failure(s)."
        )


# --- Pure register loading and classification -------------------------------------------------
#
# Everything below `load_rebrand_config` (I/O) down to `scan_text_for_findings` is pure: it takes
# already-loaded data or plain text and returns plain data structures. No filesystem or subprocess
# access, so it is fully unit-testable without a build or an install.


def load_rebrand_config(path: Path = REBRAND_JSON) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_protected_tokens(payload: dict) -> tuple[str, ...]:
    """The stable-wire-identifier register: a flat list of strings, sorted longest-first so a
    token that is a prefix of another one never clips it out from under it."""
    return tuple(sorted(payload["protected_tokens"], key=len, reverse=True))


def parse_reason_register(register_name: str, payload: dict) -> dict[str, str]:
    """Parse `accepted_residue` or `known_defects`: a list of `{"token": ..., "reason": ...}`
    objects, not bare strings -- naming them differently and requiring a stated reason for each
    is the point, so a live defect can never quietly hide behind an allowlist meant for cosmetic
    debt. Fails loudly (raises) on any entry missing a non-empty token or reason.

    Returns a `{token: reason}` mapping, ordered longest-token-first for the same reason
    `protected_tokens` is: so a short token can never clip a longer one out from under it during
    line-local containment checks.
    """
    entries = payload.get(register_name, [])
    reasons: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise VerificationFailure(
                f"{register_name} entry must be an object with 'token' and 'reason', got {entry!r}"
            )
        token = entry.get("token")
        reason = entry.get("reason")
        if not isinstance(token, str) or not token:
            raise VerificationFailure(
                f"{register_name} entry is missing a non-empty 'token': {entry!r}"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise VerificationFailure(
                f"{register_name} entry for token {token!r} is missing a non-empty 'reason'"
            )
        reasons[token] = reason
    return dict(sorted(reasons.items(), key=lambda item: len(item[0]), reverse=True))


def _find_containing_token(line: str, start: int, end: int, tokens: tuple[str, ...] | dict) -> str | None:
    """The token (if any) from `tokens` whose occurrence in `line` fully contains `line[start:end]`
    -- a pure, line-local containment check. `tokens` may be a tuple of strings or a dict keyed by
    token; either way it must already be ordered longest-first."""
    for token in tokens:
        search_from = 0
        while True:
            position = line.find(token, search_from)
            if position == -1:
                break
            if position <= start and end <= position + len(token):
                return token
            search_from = position + 1
    return None


def _is_within_protected(line: str, start: int, end: int, tokens: tuple[str, ...] | dict) -> bool:
    """Whether the match at `line[start:end]` falls entirely inside some occurrence of a token
    from `tokens` elsewhere on the same line. A thin boolean wrapper around
    `_find_containing_token`, kept because "is this masked?" reads better than a token lookup
    at every protected-token call site."""
    return _find_containing_token(line, start, end, tokens) is not None


def classify_match(
    line: str,
    start: int,
    end: int,
    protected_tokens: tuple[str, ...],
    accepted_residue: dict[str, str],
    known_defects: dict[str, str],
) -> tuple[str, str | None]:
    """Classify one leak match into exactly one of the four outcomes, checked in that order:
    silent (protected wire identifier), NOTE (accepted residue), WARNING (known defect), or FAIL
    (anything else). Returns `(outcome, token)`; `token` is the register entry that matched, or
    `None` for FAIL since nothing classified it.
    """
    token = _find_containing_token(line, start, end, protected_tokens)
    if token is not None:
        return SILENT, token
    token = _find_containing_token(line, start, end, accepted_residue)
    if token is not None:
        return NOTE, token
    token = _find_containing_token(line, start, end, known_defects)
    if token is not None:
        return WARNING, token
    return FAIL, None


@dataclass(frozen=True)
class Finding:
    line_number: int
    outcome: str
    token: str | None
    text: str


def scan_text_for_findings(
    text: str,
    protected_tokens: tuple[str, ...],
    accepted_residue: dict[str, str],
    known_defects: dict[str, str],
) -> list[Finding]:
    """Every line in `text` that mentions 'pegasus', classified into NOTE/WARNING/FAIL (silent
    hits are dropped entirely -- they are not findings, they are the design working as intended).

    Pure function: returns `Finding`s, never touches a filesystem. One finding per offending
    line -- the first non-silent match on a line is enough to classify and report it, matching
    the original design's "one violation per offending line is enough to act on".
    """
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in _LEAK_PATTERN.finditer(line):
            outcome, token = classify_match(
                line, match.start(), match.end(), protected_tokens, accepted_residue, known_defects
            )
            if outcome == SILENT:
                continue
            findings.append(Finding(line_number, outcome, token, line.strip()))
            break
    return findings


# --- I/O: running the binary and driving the checks --------------------------------------------


def _run(binary: Path, *args: str, home: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(binary), *args],
        env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
        capture_output=True, text=True, timeout=30,
    )


def _require_scratch_home(home: Path) -> None:
    real_home = Path(os.path.expanduser("~")).resolve()
    if home.resolve() == real_home:
        raise VerificationFailure(
            f"refusing to run against the real $HOME ({real_home}); pass a scratch directory"
        )


def _report_findings(report: Report, label: str, findings: list[Finding], accepted_residue: dict[str, str],
                      known_defects: dict[str, str]) -> None:
    for finding in findings:
        if finding.outcome == FAIL:
            report.fail(f"brand leak in {label}:{finding.line_number}: {finding.text}")
        elif finding.outcome == NOTE:
            reason = accepted_residue.get(finding.token, "")
            report.note(
                f"accepted residue in {label}:{finding.line_number} (token {finding.token!r}): "
                f"{finding.text} -- {reason}"
            )
        elif finding.outcome == WARNING:
            reason = known_defects.get(finding.token, "")
            report.warn(
                f"known defect in {label}:{finding.line_number} (token {finding.token!r}): "
                f"{finding.text} -- {reason}"
            )


def verify(binary: Path, scratch_root: Path) -> Report:
    report = Report()
    _require_scratch_home(scratch_root)

    home = scratch_root / "home"
    home.mkdir(parents=True)
    # A CLI adapter's own config directory has to look "detected" or a real (non-dry-run) install
    # refuses outright -- this stands in for an OpenCode install already present on the machine.
    (home / ".config" / "opencode").mkdir(parents=True)

    rebrand_config = load_rebrand_config()
    protected_tokens = parse_protected_tokens(rebrand_config)
    accepted_residue = parse_reason_register("accepted_residue", rebrand_config)
    known_defects = parse_reason_register("known_defects", rebrand_config)

    # 1. --version names darq, never pegasus.
    version_result = _run(binary, "--version", home=home)
    if version_result.returncode != 0:
        report.fail(f"'darq --version' exited {version_result.returncode}: {version_result.stderr}")
    else:
        lowered = version_result.stdout.lower()
        if "darq" in lowered:
            report.ok("'darq --version' output contains 'darq'")
        else:
            report.fail(f"'darq --version' output does not contain 'darq': {version_result.stdout!r}")
        if "pegasus" in lowered:
            report.fail(f"'darq --version' output contains 'pegasus': {version_result.stdout!r}")
        else:
            report.ok("'darq --version' output does not contain 'pegasus'")

    # 2. doctor --json: exit 0, protected schema.
    doctor_result = _run(binary, "doctor", "--json", home=home)
    if doctor_result.returncode != 0:
        report.fail(f"'darq doctor --json' exited {doctor_result.returncode}: {doctor_result.stderr}")
        doctor_payload = None
    else:
        report.ok("'darq doctor --json' exited 0")
        try:
            doctor_payload = json.loads(doctor_result.stdout)
        except json.JSONDecodeError as error:
            report.fail(f"'darq doctor --json' did not print valid JSON: {error}")
            doctor_payload = None
    if doctor_payload is not None:
        schema = doctor_payload.get("schema")
        if schema == "pegasus/cli-report/v1":
            report.ok("doctor report schema is the protected wire identifier 'pegasus/cli-report/v1'")
        else:
            report.fail(f"doctor report schema is {schema!r}, expected the protected 'pegasus/cli-report/v1'")

    # 3. install --cli opencode: exit 0.
    install_result = _run(binary, "install", "--cli", "opencode", home=home)
    if install_result.returncode != 0:
        report.fail(
            f"'darq install --cli opencode' exited {install_result.returncode}: "
            f"stdout={install_result.stdout!r} stderr={install_result.stderr!r}"
        )
    else:
        report.ok("'darq install --cli opencode' exited 0")

    # 4. Data dir is <home>/.local/share/darq; pegasus-harness's must not exist.
    darq_data_dir = home / ".local" / "share" / "darq"
    pegasus_data_dir = home / ".local" / "share" / "pegasus-harness"
    if darq_data_dir.exists():
        report.ok(f"data dir {darq_data_dir} exists")
    else:
        report.fail(f"data dir {darq_data_dir} does not exist")
    if pegasus_data_dir.exists():
        report.fail(f"data dir {pegasus_data_dir} exists and must not")
    else:
        report.ok(f"data dir {pegasus_data_dir} correctly does not exist")

    # 5. Brand leak scan, classified into silent / NOTE / WARNING / FAIL.
    config_dir = home / ".config" / "opencode"
    for path in sorted(p for p in config_dir.rglob("*") if p.is_file()):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        findings = scan_text_for_findings(text, protected_tokens, accepted_residue, known_defects)
        _report_findings(report, str(path), findings, accepted_residue, known_defects)

    for label, output in (
        ("darq --version stdout", version_result.stdout if version_result.returncode == 0 else ""),
        ("darq doctor --json stdout", doctor_result.stdout if doctor_result.returncode == 0 else ""),
    ):
        findings = scan_text_for_findings(output, protected_tokens, accepted_residue, known_defects)
        _report_findings(report, label, findings, accepted_residue, known_defects)

    if not report.failures:
        report.ok("no unclassified brand leak found (see NOTE/WARNING lines above for known residue)")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--keep-scratch", action="store_true", help="do not delete the scratch HOME afterward (for debugging)")
    arguments = parser.parse_args()

    if not arguments.binary.is_file():
        print(f"ERROR: {arguments.binary} does not exist; run tools/build_darq.py first", file=sys.stderr)
        return 1

    scratch_root = Path(tempfile.mkdtemp(prefix="darq-verify-"))
    try:
        report = verify(arguments.binary.resolve(), scratch_root)
    finally:
        if not arguments.keep_scratch:
            shutil.rmtree(scratch_root, ignore_errors=True)
        else:
            print(f"SCRATCH KEPT: {scratch_root}")

    for line in report.checks:
        print(line)

    print(f"\nSummary: {report.summary()}")

    if report.failures:
        print(f"\n{len(report.failures)} failure(s).", file=sys.stderr)
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
