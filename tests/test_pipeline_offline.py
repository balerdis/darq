"""End-to-end pipeline test with zero network: a synthetic zipapp, served through a `file://`
URL, taken through download -> hash verification -> extraction -> rebrand -> overlay.

Scope cut, deliberately: this stops short of `run_build_zipapp`/`run_build_installer`, which
invoke the *engine's own* `build_zipapp.py`/`build_installer.py` as real subprocesses. Faking
those scripts would mean re-implementing engine packaging logic inside a DARQ test, which is
exactly the kind of engine-shaped work DARQ must never take on; and running the real ones needs
the real engine tooling behaving correctly, which is out of scope for a DARQ-only pipeline test.
Everything DARQ itself is responsible for -- verifying trust, extracting, transforming, and
overlaying -- is covered end to end below.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import build_darq  # noqa: E402
from rebrand.transform import apply_to_tree, parse_map  # noqa: E402


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_url(path: Path) -> str:
    return path.resolve().as_uri()


def _build_synthetic_pegasus_zipapp() -> bytes:
    """The minimal shape `extract_pegasus_package` requires: `pegasus/__main__.py` plus a
    `pegasus/content/` file that carries the engine's brand, so the rebrand step has something
    real to rewrite."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("pegasus/__main__.py", "# synthetic pegasus entry point\n")
        archive.writestr(
            "pegasus/content/agents/pegasus-orchestrator.md",
            "---\nname: pegasus-orchestrator\n---\n# Pegasus Harness Orchestrator\n",
        )
    return buffer.getvalue()


class OfflinePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.work_root = Path(tempfile.mkdtemp(prefix="darq-pipeline-test-"))
        self.addCleanup(shutil.rmtree, self.work_root, ignore_errors=True)
        self.source_dir = self.work_root / "source"
        self.source_dir.mkdir()
        self.cache_dir = self.work_root / "cache"
        self.build_work_dir = self.work_root / "build-work"

        zipapp_bytes = _build_synthetic_pegasus_zipapp()
        sources = {
            "pegasus": zipapp_bytes,
            "build_zipapp.py": b"# not invoked in this test\n",
            "build_installer.py": b"# not invoked in this test\n",
            "install.sh": b"# not invoked in this test\n",
        }
        self.pin = {
            "tag": "vTEST",
            "assets": {
                name: {
                    "url_template": _file_url(self._write_source(name, data)),
                    "sha256": _sha256(data),
                }
                for name, data in sources.items()
            },
        }

    def _write_source(self, name: str, data: bytes) -> Path:
        path = self.source_dir / name.replace("/", "_")
        path.write_bytes(data)
        return path

    def test_download_verify_extract_rebrand_overlay_end_to_end(self) -> None:
        assets = build_darq.fetch_pinned_assets(self.pin, self.cache_dir, offline=False)

        package = build_darq.extract_pegasus_package(assets["pegasus"], self.build_work_dir)
        self.assertTrue((package / "__main__.py").is_file())

        raw_content_dir = self.work_root / "extracted-raw" / "content"
        build_darq.persist_raw_content_copy(package / "content", raw_content_dir)
        raw_marker = raw_content_dir / "agents" / "pegasus-orchestrator.md"
        self.assertTrue(raw_marker.is_file())
        self.assertIn("Pegasus Harness Orchestrator", raw_marker.read_text(encoding="utf-8"))

        rebrand_map = parse_map(json.loads((ROOT / "rebrand.json").read_text(encoding="utf-8")))
        apply_to_tree(package / "content", rebrand_map)

        # The rebranded file was renamed and its body rewritten; the old branded name is gone.
        self.assertFalse((package / "content" / "agents" / "pegasus-orchestrator.md").exists())
        rebranded = (package / "content" / "agents" / "darq-orchestrator.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("name: darq-orchestrator", rebranded)
        self.assertIn("DARQ Orchestrator", rebranded)
        self.assertNotIn("pegasus", rebranded.lower())

        # The raw copy persisted before rebranding is untouched by the in-place transform.
        self.assertIn("Pegasus Harness Orchestrator", raw_marker.read_text(encoding="utf-8"))

        overlay_dir = self.work_root / "overlay"
        (overlay_dir / "skills").mkdir(parents=True)
        (overlay_dir / "skills" / "extra.md").write_text("overlay content\n", encoding="utf-8")
        build_darq.overlay_content(package, overlay_dir, rebrand_map)
        self.assertEqual(
            (package / "content" / "skills" / "extra.md").read_text(encoding="utf-8"),
            "overlay content\n",
        )


if __name__ == "__main__":
    unittest.main()
