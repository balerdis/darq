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
    The mirror of that scan: every `accepted_residue`/`known_defects` entry must itself have
    classified at least one real hit in this run (see `find_stale_reason_entries`), or the check
    FAILs naming the stale entry, because an allowlist entry that matches nothing is a standing,
    unexercised permission for that exact string to reappear without ever failing again.
    `protected_tokens` is deliberately exempt from this mirror check -- see the comment above the
    loop that applies it in `verify()` for why.
 6. The generated `dist/install.sh`: none of 'pegasus' or 'harness' anywhere in it (unconditional
    -- there is no accepted-residue register for a file DARQ generates itself; 'balerdis' is
    deliberately not banned, see `FORBIDDEN_INSTALLER_TOKENS`'s comment -- it is the shared GitHub
    account hosting both the engine and this distribution, not an engine brand string), its
    identity header carries DARQ's own product id/names/base URL, `--help` exits 0 and never
    mentions 'pegasus' (its usage text is brand-neutral prose by template design, so it names no
    product at all -- see `verify_installer`'s docstring), and `--verify` exits 0 and names 'darq'
    in its preflight report, never 'pegasus'.
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
IDENTITY_JSON = ROOT / "identity.json"
DEFAULT_BINARY = ROOT / "dist" / "darq"
DEFAULT_INSTALLER = ROOT / "dist" / "install.sh"


def load_rebrand_config(path: Path = REBRAND_JSON) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


#: `dist/install.sh` is generated deterministically from `identity.json` by `tools/build_darq.py`
#: (via the engine's `build_installer.py`), so unlike the binary's brand-leak scan there is no
#: register of accepted residue or known defects to consult here: every one of these strings
#: appearing anywhere in the generated installer -- including its header/comments -- is
#: unconditionally a failure.
#:
#: Read from `rebrand.json`'s `forbidden_fragments` register -- the same register
#: `rebrand/transform.py`'s transform-time mirror check reads -- so there is exactly one
#: declaration of "what counts as a brand leak" inside DARQ (the engine keeps its own, separate
#: declaration upstream in `tests/brand_fragments.py`; that is out of DARQ's control and out of
#: scope here). Deliberately does NOT include 'balerdis': that is the shared GitHub account
#: hosting both the engine (github.com/balerdis/pegasus-harness) and this distribution
#: (github.com/balerdis/darq), not an engine-specific brand string. `identity.json`'s own
#: `release.install_base_url_default` legitimately contains it -- banning it would fail every
#: correctly-generated installer. What must not leak is the *engine's own* repo path, which the
#: identity-header assignment check below already catches (it asserts the header names darq's own
#: base URL, never the engine's).
FORBIDDEN_INSTALLER_TOKENS = tuple(load_rebrand_config()["forbidden_fragments"])

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
# `load_rebrand_config` itself (I/O) is defined above, next to `FORBIDDEN_INSTALLER_TOKENS`, which
# needs it at module-load time. Everything below down to `scan_text_for_findings` is pure: it
# takes already-loaded data or plain text and returns plain data structures. No filesystem or
# subprocess access, so it is fully unit-testable without a build or an install.


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


def find_stale_reason_entries(reasons: dict[str, str], corpus_texts: list[str]) -> tuple[str, ...]:
    """Tokens registered in an `accepted_residue` or `known_defects` map (already parsed by
    `parse_reason_register`) that do not literally occur anywhere in `corpus_texts` -- the exact
    texts this run scanned for brand leaks (every installed file's bytes, plus the two commands'
    rendered stdout).

    This is the guard `accepted_residue`/`known_defects` lacked: without it, an entry that no
    longer occurs classifies nothing, produces no NOTE/WARNING, and nobody notices -- the register
    only ever grows or goes stale, never shrinks, and a stale entry is a standing permission for
    that exact string to come back leaked without failing the check.

    Deliberately checks literal substring occurrence, not "won the classification for some match
    in this run": `classify_match` (via `_find_containing_token`) checks tokens longest-first and
    returns the first one whose occurrence fully contains the match, so a *shorter* registered
    token whose every occurrence happens to sit inside a *longer* registered token's occurrence
    will never be returned as the winning classifier -- the longer entry always claims that match
    first. That is expected overlap between two live entries, not the shorter one being obsolete:
    both tokens are still genuinely present in the artifact, just at the same spot. Testing literal
    presence in the corpus instead of "ever won a classification" keeps a shadowed-but-present
    token out of this stale list; only a token that plain-text never occurs at all -- winning or
    losing a classification -- is reported.

    Pure: takes already-collected text and an already-parsed register, returns plain data.
    """
    return tuple(token for token in reasons if not any(token in text for text in corpus_texts))


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


def find_installer_brand_leaks(
    text: str, tokens: tuple[str, ...] = FORBIDDEN_INSTALLER_TOKENS
) -> list[tuple[int, str, str]]:
    """Every line of `text` mentioning (case-insensitively) any of `tokens`, as
    `(line_number, token, line_text)`.

    Unlike `scan_text_for_findings`, there is no register here to sort a hit into NOTE/WARNING/
    silent: `install.sh` is generated deterministically from `identity.json`, with no upstream
    residue to account for, so every hit this finds is unconditionally a failure. Pure: takes
    already-read text, returns plain data, touches no filesystem.
    """
    findings: list[tuple[int, str, str]] = []
    lowered_tokens = tuple(token.lower() for token in tokens)
    for line_number, line in enumerate(text.splitlines(), start=1):
        lowered_line = line.lower()
        for token in lowered_tokens:
            if token in lowered_line:
                findings.append((line_number, token, line.strip()))
                break
    return findings


def expected_installer_identity_assignments(identity: dict) -> dict[str, str]:
    """The four `NAME='value'` identity-header assignments `dist/install.sh` must carry, derived
    from `identity.json` the same way `build_installer.py::render` derives them -- so this check
    can never quietly drift from what the generator actually fills in. Pure: takes an
    already-parsed `identity.json` payload, returns plain data.
    """
    return {
        "PRODUCT_ID": identity["product_id"],
        "PRODUCT_DISPLAY_NAME": identity["display_name"],
        "PRODUCT_PROGRAM_NAME": identity["program_name"],
        "PRODUCT_RELEASE_BASE_URL_DEFAULT": identity["release"]["install_base_url_default"],
    }


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


def verify_installer(installer: Path, scratch_root: Path, report: Report) -> None:
    """Behavioural verification of the generated `dist/install.sh`, run the same way
    `verify()` runs the binary: real bytes scanned, and the installer run for real (twice, in two
    safe modes), inside a throwaway `HOME` this function never lets be the real one.

    Runs both `--help` and `--verify`, never a bare `./install.sh`: reading the template
    (`tools/build_installer.py`'s source, and `install.sh`'s own top-of-file usage comment)
    confirms `--verify` only ever reads the environment (`command -v`, file-existence checks
    under `$HOME`) to report what it *would* install -- it never downloads or writes anything,
    in or outside the scratch `HOME` this passes it.

    The two modes are not redundant: `uso()` (what `--help` prints) is, by the template's own
    design, the literal top-of-file comment block -- generic prose ("este producto") that never
    names any product, this distribution's or the engine's, so it only proves the installer parses
    and exits 0. The identity header actually surfacing is instead proven by `--verify`'s preflight
    report, which names `$PRODUCT_PROGRAM_NAME` directly (confirmed by running the real generated
    installer: `--verify` under a restricted PATH prints lines like "el binario darq, en ..." and
    "se lanzaría: darq"). Both runs use a `PATH` restricted to `/usr/bin:/bin`, the same restriction
    `verify()`'s own `_run` applies to the built binary, so neither run can pick up this machine's
    own real Node/OpenCode/darq and produce a false pass or a spurious pipefail crash from a
    broken local install.
    """
    if not installer.is_file():
        report.fail(f"installer {installer} does not exist; run tools/build_darq.py first")
        return

    text = installer.read_text(encoding="utf-8")
    leaks = find_installer_brand_leaks(text)
    if leaks:
        for line_number, token, line_text in leaks:
            report.fail(
                f"installer brand leak in {installer}:{line_number} (token {token!r}): {line_text}"
            )
    else:
        report.ok(f"{installer} contains none of {FORBIDDEN_INSTALLER_TOKENS}")

    identity = json.loads(IDENTITY_JSON.read_text(encoding="utf-8"))
    for name, value in expected_installer_identity_assignments(identity).items():
        assignment = f"{name}='{value}'"
        if assignment in text:
            report.ok(f"installer identity header carries {assignment}")
        else:
            report.fail(f"installer identity header is missing expected assignment {assignment!r}")

    home = scratch_root / "installer-home"
    home.mkdir(parents=True, exist_ok=True)
    _require_scratch_home(home)
    restricted_env = {"HOME": str(home), "PATH": "/usr/bin:/bin"}

    help_result = subprocess.run(
        ["bash", str(installer), "--help"], env=restricted_env,
        capture_output=True, text=True, timeout=30,
    )
    if help_result.returncode != 0:
        report.fail(
            f"'bash {installer} --help' exited {help_result.returncode}: {help_result.stderr}"
        )
    else:
        report.ok("'install.sh --help' exited 0")
    if "pegasus" in help_result.stdout.lower() or "pegasus" in help_result.stderr.lower():
        report.fail(f"'install.sh --help' output mentions 'pegasus': {help_result.stdout!r}")
    else:
        report.ok("'install.sh --help' output does not mention 'pegasus'")

    # `--verify` never installs or downloads anything (confirmed by reading the template and by
    # running it here): it only inspects the environment and prints what a real run would do, so
    # it is the one place that actually proves the identity header reached the printed output.
    verify_result = subprocess.run(
        ["bash", str(installer), "--verify"], env=restricted_env,
        capture_output=True, text=True, timeout=30,
    )
    if verify_result.returncode != 0:
        report.fail(
            f"'bash {installer} --verify' exited {verify_result.returncode}: "
            f"stdout={verify_result.stdout!r} stderr={verify_result.stderr!r}"
        )
    else:
        report.ok("'install.sh --verify' exited 0")
    combined_output = verify_result.stdout + verify_result.stderr
    lowered_output = combined_output.lower()
    if "darq" in lowered_output:
        report.ok("'install.sh --verify' output names 'darq'")
    else:
        report.fail(f"'install.sh --verify' output does not mention 'darq': {combined_output!r}")
    if "pegasus" in lowered_output:
        report.fail(f"'install.sh --verify' output mentions 'pegasus': {combined_output!r}")
    else:
        report.ok("'install.sh --verify' output does not mention 'pegasus'")


def verify(binary: Path, scratch_root: Path, installer: Path = DEFAULT_INSTALLER) -> Report:
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
    scanned_corpus: list[str] = []
    config_dir = home / ".config" / "opencode"
    for path in sorted(p for p in config_dir.rglob("*") if p.is_file()):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned_corpus.append(text)
        findings = scan_text_for_findings(text, protected_tokens, accepted_residue, known_defects)
        _report_findings(report, str(path), findings, accepted_residue, known_defects)

    for label, output in (
        ("darq --version stdout", version_result.stdout if version_result.returncode == 0 else ""),
        ("darq doctor --json stdout", doctor_result.stdout if doctor_result.returncode == 0 else ""),
    ):
        scanned_corpus.append(output)
        findings = scan_text_for_findings(output, protected_tokens, accepted_residue, known_defects)
        _report_findings(report, label, findings, accepted_residue, known_defects)

    if not report.failures:
        report.ok("no unclassified brand leak found (see NOTE/WARNING lines above for known residue)")

    # 5b. The mirror of the scan above: every accepted_residue/known_defects entry must itself
    # have classified at least one real hit in this run, or it is a stale allowlist entry -- a
    # standing, unexercised permission for that exact string to leak back in without failing.
    #
    # `protected_tokens` deliberately does NOT get this same guard, for two independent reasons:
    #   1. Direction of risk. accepted_residue/known_defects each *excuse* an occurrence of the
    #      brand that would otherwise fail the check -- a stale entry there is a live permission
    #      for a regression to slip back in silently, which is exactly the failure mode this task
    #      is closing. protected_tokens does the opposite: it marks a string SILENT, i.e. the
    #      scan's strictest, safest outcome. A protected_tokens entry that currently matches
    #      nothing costs nothing if it stays registered -- it can never mask a brand-leak
    #      regression, because nothing is being excused, only a wire identifier is being
    #      recognised. There is no latent-permission risk here to guard against.
    #   2. What it actually protects. protected_tokens exists to keep stable wire identifiers
    #      (schema strings, env var names, journal/report keys, data-dir prefixes) byte-identical
    #      even when some of them only ever surface on install paths this run's single
    #      `darq install --cli opencode` doesn't exercise (e.g. an env var only written for a
    #      different --cli target). Demanding a hit every run would force pruning entries that
    #      are correct and still needed, just not exercised by *this* scenario -- unlike
    #      accepted_residue/known_defects, which this run's scan corpus is specifically meant to
    #      cover completely.
    for register_name, reasons in (("accepted_residue", accepted_residue), ("known_defects", known_defects)):
        for token in find_stale_reason_entries(reasons, scanned_corpus):
            report.fail(
                f"{register_name} entry {token!r} matched no hit in this run; remove it from "
                "rebrand.json -- an entry that classifies nothing is a stale allowlist grant, "
                "not evidence of anything to fix"
            )

    # 6. The generated installer: brand-free, identity header correct, --help works and names darq.
    verify_installer(installer, scratch_root, report)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--installer", type=Path, default=DEFAULT_INSTALLER)
    parser.add_argument("--keep-scratch", action="store_true", help="do not delete the scratch HOME afterward (for debugging)")
    arguments = parser.parse_args()

    if not arguments.binary.is_file():
        print(f"ERROR: {arguments.binary} does not exist; run tools/build_darq.py first", file=sys.stderr)
        return 1
    if not arguments.installer.is_file():
        print(f"ERROR: {arguments.installer} does not exist; run tools/build_darq.py first", file=sys.stderr)
        return 1

    scratch_root = Path(tempfile.mkdtemp(prefix="darq-verify-"))
    try:
        report = verify(arguments.binary.resolve(), scratch_root, arguments.installer.resolve())
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
