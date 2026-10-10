"""A release endpoint that stops answering (a repository made private, a
network that is down, a rate limit, an unreadable body) never ends in a raw
Python traceback.

Two behaviours are proven here, each against every failure shape:

* the *automatic* check (`cli.check_for_update`, behind the TUI's notice)
  stays silent -- `None`, nothing written to `out`, no exception;
* the *explicit* `upgrade` (CLI flags and the TUI's Upgrade entry) says in
  plain words that the release information could not be reached, why, and
  what to do, then exits non-zero / returns to a result screen, with no
  traceback text anywhere.

The failures reach the engine two ways: as `DownloaderError`s with the
status `HttpDownloader` attaches (what the engine sees), and as the real
`urllib` exceptions fed through `HttpDownloader` itself with `urlopen`
patched (proving the status and the rate-limit flag are attached at all).
No socket is ever opened.
"""
from __future__ import annotations

import email.message
import http.client
import io
import json
import socket
import unittest
import urllib.error
import zipfile
import tempfile
from pathlib import Path
from unittest.mock import patch

from fakes import FakeDownloader, FakeFileSystem
from darq import cli
from darq.core import upgrade as upgrade_module
from darq.infra.downloader_http import HttpDownloader
from darq.ports.downloader import DownloaderError
from darq.tui import session
from darq.tui.navigator import Action, InstallPlanScreen, InstallResultScreen, Navigator
from test_cli_upgrade import release_body, sha256sum_line

AT = "2026-08-14T00:00:00+00:00"
HOME = Path("/home/person")
RELEASE = cli.default_identity().release
API = RELEASE.latest_release_api_url
NEWER = "99.0.0"

NO_TRACEBACK = ("Traceback", "File \"", "DownloaderError", "HTTPError", "JSONDecodeError", "KeyError")


def _headers(**fields: str) -> email.message.Message:
    message = email.message.Message()
    for name, value in fields.items():
        message[name.replace("_", "-")] = value
    return message


def _http_error(code: int, **headers: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(API, code, "reason", _headers(**headers), None)


#: name -> (what `urlopen` raises or returns, text the explicit upgrade must say)
RAISING_FAILURES = {
    "404": (_http_error(404), ["HTTP 404", "not found", "private or unreachable", "locally built binary"]),
    "401": (_http_error(401), ["HTTP 401", "no access", "private or unreachable", "locally built binary"]),
    "403": (_http_error(403), ["HTTP 403", "no access", "private or unreachable", "locally built binary"]),
    "rate limit 403": (
        _http_error(403, X_RateLimit_Remaining="0"),
        ["rate-limiting", "HTTP 403", "wait a while"],
    ),
    "rate limit 429": (_http_error(429, Retry_After="60"), ["rate-limiting", "HTTP 429"]),
    "server error": (_http_error(503), ["HTTP 503", "try again later"]),
    "url error": (
        urllib.error.URLError(socket.gaierror(-2, "Name or service not known")),
        ["network error", "Name or service not known", "try again"],
    ),
    "timeout": (TimeoutError("timed out"), ["network error", "timed out", "try again"]),
    "dropped connection": (http.client.IncompleteRead(b"x"), ["network error", "try again"]),
}


class RaisingUrlopen:
    """What `urlopen` does for one failure: raise it."""

    def __init__(self, error: BaseException):
        self.error = error

    def __call__(self, url, timeout=None):
        raise self.error


class RealDownloaderFor(FakeDownloader):
    """A downloader that runs the real `HttpDownloader` -- with `urlopen`
    patched to raise `error` for the release API URL -- so the status and
    rate-limit flag the engine sees are the ones the real adapter produces."""

    def __init__(self, error: BaseException, responses=None):
        super().__init__(responses)
        self._error = error
        self._real = HttpDownloader()

    def fetch(self, url, *, timeout_seconds=None, on_progress=None):
        if url in self.responses:
            return super().fetch(url, timeout_seconds=timeout_seconds, on_progress=on_progress)
        self.calls.append(url)
        with patch("darq.infra.downloader_http.urllib.request.urlopen", RaisingUrlopen(self._error)):
            return self._real.fetch(url, timeout_seconds=timeout_seconds)



def _assert_clean(test: unittest.TestCase, text: str) -> None:
    for fragment in NO_TRACEBACK:
        test.assertNotIn(fragment, text)


class HttpDownloaderKeepsTheStatusTest(unittest.TestCase):
    def fetch_error(self, error: BaseException) -> DownloaderError:
        with patch("darq.infra.downloader_http.urllib.request.urlopen", RaisingUrlopen(error)):
            with self.assertRaises(DownloaderError) as caught:
                HttpDownloader().fetch(API)
        return caught.exception

    def test_a_404_carries_its_status(self):
        error = self.fetch_error(_http_error(404))
        self.assertEqual((error.status, error.rate_limited), (404, False))

    def test_a_plain_403_is_a_refusal_not_a_rate_limit(self):
        error = self.fetch_error(_http_error(403))
        self.assertEqual((error.status, error.rate_limited), (403, False))

    def test_a_403_with_an_exhausted_budget_is_a_rate_limit(self):
        error = self.fetch_error(_http_error(403, X_RateLimit_Remaining="0"))
        self.assertEqual((error.status, error.rate_limited), (403, True))

    def test_a_403_with_retry_after_is_a_rate_limit(self):
        self.assertTrue(self.fetch_error(_http_error(403, Retry_After="30")).rate_limited)

    def test_a_429_is_a_rate_limit(self):
        self.assertTrue(self.fetch_error(_http_error(429)).rate_limited)

    def test_a_transport_failure_has_no_status(self):
        error = self.fetch_error(urllib.error.URLError("no route"))
        self.assertIsNone(error.status)
        self.assertFalse(error.rate_limited)

    def test_a_timeout_has_no_status(self):
        self.assertIsNone(self.fetch_error(TimeoutError("timed out")).status)


class AutomaticCheckStaysSilentTest(unittest.TestCase):
    def runtime(self, downloader) -> cli.Runtime:
        return cli.Runtime(
            filesystem=FakeFileSystem(), home=HOME, now=AT, out=io.StringIO(), variables={}, downloader=downloader
        )

    def test_every_failure_answers_none_and_prints_nothing(self):
        for name, (error, _) in RAISING_FAILURES.items():
            with self.subTest(name):
                runtime = self.runtime(RealDownloaderFor(error))
                self.assertIsNone(cli.check_for_update(runtime))
                self.assertEqual(runtime.out.getvalue(), "")

    def test_an_invalid_body_answers_none_and_prints_nothing(self):
        for name, body in {"not json": b"<html>Not Found</html>", "binary": b"\xff\xfe", "list": b"[]", "no tag": b"{}"}.items():
            with self.subTest(name):
                runtime = self.runtime(FakeDownloader({API: body}))
                self.assertIsNone(cli.check_for_update(runtime))
                self.assertEqual(runtime.out.getvalue(), "")

    def test_a_failure_is_not_retried_within_the_hour(self):
        """No repeated nag: the failure is cached so the next launch does not ask again."""
        downloader = RealDownloaderFor(_http_error(404))
        filesystem = FakeFileSystem()
        runtime = cli.Runtime(
            filesystem=filesystem, home=HOME, now=AT, out=io.StringIO(), variables={}, downloader=downloader
        )
        cli.check_for_update(runtime)
        cli.check_for_update(runtime)
        self.assertEqual(downloader.calls.count(API), 1)


class ExplicitUpgradeTestCase(unittest.TestCase):
    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._directory.cleanup)
        self.destination = Path(self._directory.name) / "darq"
        with zipfile.ZipFile(self.destination, "w") as archive:
            archive.writestr("__main__.py", "pass\n")

    def runtime(self, downloader) -> cli.Runtime:
        return cli.Runtime(
            filesystem=FakeFileSystem(files={self.destination: b"old bytes"}),
            home=HOME,
            now=AT,
            out=io.StringIO(),
            variables={},
            downloader=downloader,
            sys_path0=str(self.destination),
        )

    def good_responses(self, content: bytes = b"new bytes") -> dict[str, bytes]:
        return {
            API: release_body(f"v{NEWER}"),
            upgrade_module.checksum_url(NEWER, RELEASE): sha256sum_line(content),
            upgrade_module.binary_url(NEWER, RELEASE): content,
        }


class ExplicitUpgradeCliTest(ExplicitUpgradeTestCase):
    def run_main(self, downloader, *extra: str) -> tuple[int, str]:
        runtime = self.runtime(downloader)
        code = cli.main(["upgrade", *extra], runtime=runtime)
        return code, runtime.out.getvalue()

    def test_every_release_api_failure_is_a_clear_message_and_a_nonzero_exit(self):
        for name, (error, expected) in RAISING_FAILURES.items():
            with self.subTest(name):
                code, output = self.run_main(RealDownloaderFor(error))
                self.assertEqual(code, cli.FAILED)
                self.assertIn("could not get the newest published release information", output)
                for fragment in expected:
                    self.assertIn(fragment, output)
                _assert_clean(self, output)

    def test_an_invalid_body_is_a_clear_message_and_a_nonzero_exit(self):
        for name, body in {"not json": b"<html>Not Found</html>", "binary": b"\xff\xfe", "list": b"[]", "no tag": b"{}"}.items():
            with self.subTest(name):
                code, output = self.run_main(FakeDownloader({API: body}))
                self.assertEqual(code, cli.FAILED)
                self.assertIn("could not get the newest published release information", output)
                self.assertIn("not a release description", output)
                _assert_clean(self, output)

    def test_the_json_report_is_a_failed_report_not_a_traceback(self):
        code, output = self.run_main(RealDownloaderFor(_http_error(404)), "--json")
        self.assertEqual(code, cli.FAILED)
        document = json.loads(output)
        self.assertEqual(document["status"], "failed")
        self.assertIn("private or unreachable", document["error"])

    def test_nothing_is_replaced_when_the_check_fails(self):
        runtime = self.runtime(RealDownloaderFor(_http_error(404)))
        cli.main(["upgrade"], runtime=runtime)
        self.assertEqual(runtime.filesystem.writes, [])

    def test_a_programming_error_is_not_swallowed(self):
        class Broken:
            def fetch(self, url, *, timeout_seconds=None, on_progress=None):
                raise AttributeError("a bug, not a network failure")

        with self.assertRaises(AttributeError):
            self.run_main(Broken())

    def test_every_asset_failure_after_a_good_check_is_clean_too(self):
        for asset_name, asset_url in {
            "checksum": upgrade_module.checksum_url(NEWER, RELEASE),
            "binary": upgrade_module.binary_url(NEWER, RELEASE),
        }.items():
            for name, (error, expected) in RAISING_FAILURES.items():
                with self.subTest(asset=asset_name, failure=name):
                    responses = self.good_responses()
                    del responses[asset_url]
                    code, output = self.run_main(RealDownloaderFor(error, responses))
                    self.assertEqual(code, cli.FAILED)
                    self.assertIn(f"could not fetch the {asset_name}", output)
                    for fragment in expected:
                        self.assertIn(fragment, output)
                    _assert_clean(self, output)

    def test_a_failed_asset_download_replaces_nothing(self):
        responses = self.good_responses()
        del responses[upgrade_module.binary_url(NEWER, RELEASE)]
        runtime = self.runtime(RealDownloaderFor(_http_error(404), responses))
        cli.main(["upgrade"], runtime=runtime)
        self.assertEqual(runtime.filesystem.files[self.destination], b"old bytes")

    def test_a_working_endpoint_still_upgrades(self):
        code, output = self.run_main(FakeDownloader(self.good_responses()))
        self.assertEqual(code, cli.OK)
        self.assertIn(NEWER, output)


class ExplicitUpgradeTuiTest(ExplicitUpgradeTestCase):
    def to_upgrade(self) -> Navigator:
        navigator = Navigator.starting()
        index = [entry.label for entry in navigator.current.entries].index("Upgrade")
        for _ in range(index):
            navigator = navigator.handle(Action.MOVE_DOWN)
        return navigator

    def test_a_failed_check_lands_on_a_result_screen_naming_the_reason(self):
        for name, (error, expected) in RAISING_FAILURES.items():
            with self.subTest(name):
                runtime = self.runtime(RealDownloaderFor(error))
                navigator = session.step(self.to_upgrade(), runtime, Action.CHOOSE)
                self.assertIsInstance(navigator.current, InstallResultScreen)
                report = navigator.current.report
                self.assertEqual(report["status"], "failed")
                for fragment in expected:
                    self.assertIn(fragment, report["error"])
                _assert_clean(self, report["error"])

    def test_the_result_screen_returns_to_the_menu(self):
        runtime = self.runtime(RealDownloaderFor(_http_error(404)))
        navigator = session.step(self.to_upgrade(), runtime, Action.CHOOSE)
        navigator = session.step(navigator, runtime, Action.CHOOSE)
        self.assertNotIsInstance(navigator.current, InstallResultScreen)

    def test_an_asset_failure_after_confirming_lands_on_a_clean_result_screen(self):
        responses = self.good_responses()
        del responses[upgrade_module.binary_url(NEWER, RELEASE)]
        runtime = self.runtime(RealDownloaderFor(_http_error(404), responses))
        navigator = session.step(self.to_upgrade(), runtime, Action.CHOOSE)
        self.assertIsInstance(navigator.current, InstallPlanScreen)
        navigator = session.step(navigator, runtime, Action.CHOOSE)
        self.assertIsInstance(navigator.current, InstallResultScreen)
        self.assertEqual(navigator.current.report["status"], "failed")
        self.assertIn("could not fetch the binary", navigator.current.report["error"])
        _assert_clean(self, navigator.current.report["error"])


if __name__ == "__main__":
    unittest.main()
