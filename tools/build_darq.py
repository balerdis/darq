#!/usr/bin/env python3
"""Build the `darq` distribution artifact from a pinned, published pegasus release.

DARQ contains zero engine code and zero copies of engine content. Every build starts from the
`pegasus` binary and `build_zipapp.py` published at the exact tag pinned in `engine.pin`,
verifies both against the sha256 pinned there (the trust boundary: any mismatch is a hard
refusal, never a warning), rebrands the extracted content tree in place with
`rebrand/transform.py`, overlays this repo's own `content/` on top, and finally reuses the
downloaded `build_zipapp.py` -- never a local copy of the engine's -- to produce `dist/darq`.

    python3 tools/build_darq.py
    python3 tools/build_darq.py --offline   # reuse whatever is already in the cache dir

I/O (downloading, extracting, writing) is kept in this module; `rebrand.transform` and this
module's own pure helpers below hold no I/O of their own beyond what is unavoidable to drive them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rebrand.transform import RebrandMap, apply_to_tree, parse_map  # noqa: E402

ENGINE_PIN = ROOT / "engine.pin"
REBRAND_JSON = ROOT / "rebrand.json"
IDENTITY_JSON = ROOT / "identity.json"
CONTENT_OVERLAY = ROOT / "content"
DEFAULT_CACHE_DIR = ROOT / "build" / "cache"
DEFAULT_WORK_DIR = ROOT / "build" / "work"
DEFAULT_OUT = ROOT / "dist" / "darq"


class BuildError(RuntimeError):
    """The build cannot proceed. Always fatal -- there is no partial or best-effort build."""


def load_pin(path: Path = ENGINE_PIN) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def asset_url(pin: dict, asset_name: str) -> str:
    tag = pin["tag"]
    template = pin["assets"][asset_name]["url_template"]
    return template.format(tag=tag)


def expected_sha256(pin: dict, asset_name: str) -> str:
    return pin["assets"][asset_name]["sha256"]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, destination.open("wb") as handle:  # noqa: S310
        shutil.copyfileobj(response, handle)


def fetch_pinned_assets(pin: dict, cache_dir: Path, *, offline: bool) -> dict[str, Path]:
    """Download (or reuse, when `offline`) `pegasus` and `build_zipapp.py` into `cache_dir`,
    then verify both against `engine.pin` unconditionally -- verification is never skipped, even
    when the download itself was.
    """
    paths: dict[str, Path] = {}
    for asset_name in ("pegasus", "build_zipapp.py"):
        destination = cache_dir / asset_name
        if offline and destination.is_file():
            print(f"OFFLINE: reusing cached {asset_name} at {destination}")
        else:
            url = asset_url(pin, asset_name)
            print(f"FETCH: {asset_name} <- {url}")
            download(url, destination)
        paths[asset_name] = destination

    for asset_name, path in paths.items():
        if not path.is_file():
            raise BuildError(
                f"{asset_name} is not present at {path}; run without --offline to download it"
            )
        actual = sha256_of(path)
        expected = expected_sha256(pin, asset_name)
        if actual != expected:
            raise BuildError(
                f"REFUSED: {asset_name} sha256 mismatch -- expected {expected}, got {actual}. "
                f"This is the trust boundary between DARQ and the pinned pegasus release; a "
                f"mismatch is never a warning."
            )
        print(f"VERIFIED: {asset_name} sha256 {actual} matches engine.pin")
    return paths


def extract_pegasus_package(pegasus_binary: Path, work_dir: Path) -> Path:
    """Extract the published `pegasus` zipapp and return `<work_dir>/extracted/pegasus`."""
    extracted = work_dir / "extracted"
    if extracted.exists():
        shutil.rmtree(extracted)
    if not zipfile.is_zipfile(pegasus_binary):
        raise BuildError(f"{pegasus_binary} is not a valid zipapp (zipfile.is_zipfile() is False)")
    with zipfile.ZipFile(pegasus_binary) as archive:
        archive.extractall(extracted)
    package = extracted / "pegasus"
    if not (package / "__main__.py").is_file():
        raise BuildError(f"{package} has no __main__.py; extraction did not produce the expected layout")
    return package


def overlay_content(package: Path, overlay_root: Path) -> None:
    """Copy every file from `overlay_root` into `<package>/content`, adding to and replacing by
    path, never wiping the inherited tree the rebrand transform already rewrote.
    """
    if not overlay_root.is_dir():
        return
    destination_root = package / "content"
    for source_path in sorted(p for p in overlay_root.rglob("*") if p.is_file()):
        relative = source_path.relative_to(overlay_root)
        destination_path = destination_root / relative
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        print(f"OVERLAY: {relative}")


def run_build_zipapp(build_zipapp_py: Path, source: Path, identity: Path, out: Path) -> None:
    if out.exists():
        out.unlink()
    result = subprocess.run(
        [sys.executable, str(build_zipapp_py), "--source", str(source), "--identity", str(identity), "--out", str(out)],
        capture_output=True, text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        raise BuildError(f"build_zipapp.py failed with exit code {result.returncode}")


def build(*, offline: bool, cache_dir: Path = DEFAULT_CACHE_DIR, work_dir: Path = DEFAULT_WORK_DIR, out: Path = DEFAULT_OUT) -> Path:
    pin = load_pin()
    print(f"PIN: pegasus-harness tag {pin['tag']}")

    assets = fetch_pinned_assets(pin, cache_dir, offline=offline)

    work_dir.mkdir(parents=True, exist_ok=True)
    package = extract_pegasus_package(assets["pegasus"], work_dir)
    print(f"EXTRACTED: {package}")

    rebrand_map = parse_map(json.loads(REBRAND_JSON.read_text(encoding="utf-8")))
    apply_to_tree(package / "content", rebrand_map)
    print("REBRANDED: content tree rewritten in place")

    overlay_content(package, CONTENT_OVERLAY)

    out.parent.mkdir(parents=True, exist_ok=True)
    run_build_zipapp(assets["build_zipapp.py"], package, IDENTITY_JSON, out)

    checksum_path = out.with_name(out.name + ".sha256")
    if not checksum_path.is_file():
        raise BuildError(f"build_zipapp.py did not write {checksum_path}")
    print(f"BUILT: {out}")
    print(f"CHECKSUM: {checksum_path.read_text(encoding='utf-8').strip()}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="reuse cached assets instead of downloading; verification still runs unconditionally")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    arguments = parser.parse_args()
    try:
        build(offline=arguments.offline, cache_dir=arguments.cache_dir, work_dir=arguments.work_dir, out=arguments.out)
    except BuildError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
