#!/usr/bin/env python3
"""Build the `darq` distribution artifact from a pinned, published pegasus release.

DARQ contains zero engine code and zero copies of engine content. Every build starts from the
`pegasus` binary, `build_zipapp.py`, `build_installer.py` and the `install.sh` template published
at the exact tag pinned in `engine.pin`, verifies all four against the sha256 pinned there (the
trust boundary: any mismatch is a hard refusal, never a warning), rebrands the extracted content
tree in place with `rebrand/transform.py`, overlays this repo's own `content/` on top, and finally
reuses the downloaded `build_zipapp.py` and `build_installer.py` -- never a local copy of the
engine's -- to produce `dist/darq` and `dist/install.sh`.

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
def raw_content_dir_for(work_dir: Path) -> Path:
    """Where the engine's content tree is persisted *before* `rebrand.transform.apply_to_tree`
    rewrites it in place, for a given `work_dir`. Always a sibling of `<work_dir>/extracted`, so
    two builds run with different `--work-dir` values never collide on the same raw copy location.

    This is verification input only -- it sits outside `<work_dir>/extracted/pegasus`, the tree
    that `run_build_zipapp`/`run_build_installer` package, so it never reaches `dist/`. See
    `tests/test_build_darq.py::RawContentCopyTests` for the checks that it stays out of what gets
    packaged and that it derives from `work_dir` rather than a fixed path.
    """
    return work_dir / "extracted-raw" / "content"


#: `raw_content_dir_for`'s value for `DEFAULT_WORK_DIR`, kept as today's default so passing no
#: `--work-dir` changes nothing.
DEFAULT_RAW_CONTENT_DIR = raw_content_dir_for(DEFAULT_WORK_DIR)
DEFAULT_OUT = ROOT / "dist" / "darq"
DEFAULT_INSTALLER_OUT = ROOT / "dist" / "install.sh"

#: Every asset `engine.pin` pins and this build downloads (or reuses, under `--offline`) and
#: verifies unconditionally. Order is insignificant -- `fetch_pinned_assets` verifies all of them
#: before any is used -- but is kept stable here for readable build logs.
PINNED_ASSETS = ("pegasus", "build_zipapp.py", "build_installer.py", "install.sh")


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
    """Download (or reuse, when `offline`) every asset in `PINNED_ASSETS` into `cache_dir`, then
    verify all of them against `engine.pin` unconditionally -- verification is never skipped, even
    when the download itself was.
    """
    paths: dict[str, Path] = {}
    for asset_name in PINNED_ASSETS:
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


def persist_raw_content_copy(content_root: Path, raw_content_dir: Path) -> None:
    """Copy `content_root` (the freshly extracted, not-yet-rebranded `pegasus/content` tree) to
    `raw_content_dir` before `apply_to_tree` rewrites `content_root` in place.

    This is the only copy of the engine's raw content DARQ ever persists, and it exists solely so
    `tests/test_rebrand.py` can assert what the transform actually *derives* from real engine
    content, rather than asserting idempotence against content the previous build already
    rewrote. It is never read by the build itself again and must never be packaged -- see
    `DEFAULT_RAW_CONTENT_DIR`'s docstring for how that is kept true.
    """
    if raw_content_dir.exists():
        shutil.rmtree(raw_content_dir)
    raw_content_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(content_root, raw_content_dir)


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


def format_checksum_sidecar(sha256_digest: str, filename: str) -> str:
    """The exact `.sha256` sidecar format `build_zipapp.py` already writes for `dist/darq`
    (`"<digest>  <filename>\\n"`), reused here so `dist/install.sh.sha256` matches it byte for byte
    rather than inventing a second, subtly different checksum format for the same repo.
    """
    return f"{sha256_digest}  {filename}\n"


def run_build_installer(
    build_installer_py: Path, template: Path, package_source: Path, identity: Path, out: Path
) -> None:
    """Generate `dist/install.sh` by invoking the engine's own `build_installer.py` -- never a
    local reimplementation of its templating -- against the downloaded, verified `install.sh`
    template, DARQ's own `identity.json`, and the extracted `pegasus` package tree (used only to
    validate the identity, per `build_installer.py --package-source`).
    """
    if out.exists():
        out.unlink()
    result = subprocess.run(
        [
            sys.executable, str(build_installer_py),
            "--template", str(template),
            "--package-source", str(package_source),
            "--identity", str(identity),
            "--out", str(out),
        ],
        capture_output=True, text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        raise BuildError(f"build_installer.py failed with exit code {result.returncode}")
    if not out.is_file():
        raise BuildError(f"build_installer.py exited 0 but did not write {out}")

    checksum_path = out.with_name(out.name + ".sha256")
    checksum_path.write_text(format_checksum_sidecar(sha256_of(out), out.name), encoding="utf-8")
    print(f"WROTE checksum: {checksum_path}")


def build(
    *,
    offline: bool,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    work_dir: Path = DEFAULT_WORK_DIR,
    out: Path = DEFAULT_OUT,
    installer_out: Path = DEFAULT_INSTALLER_OUT,
    raw_content_dir: Path | None = None,
) -> Path:
    """`raw_content_dir` defaults to `raw_content_dir_for(work_dir)` -- a sibling of
    `work_dir/extracted` -- rather than to a fixed path, so a custom `work_dir` never collides
    with another build's raw content copy. Pass it explicitly only to override that derivation."""
    pin = load_pin()
    print(f"PIN: pegasus-harness tag {pin['tag']}")

    if raw_content_dir is None:
        raw_content_dir = raw_content_dir_for(work_dir)

    assets = fetch_pinned_assets(pin, cache_dir, offline=offline)

    work_dir.mkdir(parents=True, exist_ok=True)
    package = extract_pegasus_package(assets["pegasus"], work_dir)
    print(f"EXTRACTED: {package}")

    persist_raw_content_copy(package / "content", raw_content_dir)
    print(f"PERSISTED: raw (unrebranded) content copy at {raw_content_dir}")

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

    installer_out.parent.mkdir(parents=True, exist_ok=True)
    run_build_installer(assets["build_installer.py"], assets["install.sh"], package, IDENTITY_JSON, installer_out)
    installer_checksum_path = installer_out.with_name(installer_out.name + ".sha256")
    print(f"BUILT: {installer_out}")
    print(f"CHECKSUM: {installer_checksum_path.read_text(encoding='utf-8').strip()}")

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="reuse cached assets instead of downloading; verification still runs unconditionally")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--installer-out", type=Path, default=DEFAULT_INSTALLER_OUT)
    arguments = parser.parse_args()
    try:
        build(
            offline=arguments.offline,
            cache_dir=arguments.cache_dir,
            work_dir=arguments.work_dir,
            out=arguments.out,
            installer_out=arguments.installer_out,
        )
    except BuildError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
