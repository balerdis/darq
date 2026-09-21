#!/usr/bin/env python3
"""Build a distribution's own `install.sh` from its `identity.json`.

`install.sh` is engine infrastructure, not something a distribution should fork: 1000-odd lines
of installer logic copied into a distribution's own repository would diverge on the first upstream
change, exactly what the distribution build path exists to prevent. Instead the checked-in
`install.sh` carries a single, clearly delimited identity header block -- the shell analogue of
`cli.py`'s composition root -- and this script regenerates just that block from a given
`identity.json`, leaving every other line of the template byte-for-byte untouched.

    python3 tools/build_installer.py --identity src/pegasus/identity.json --out dist/install.sh

Pegasus's own release build runs this with its own `src/pegasus/identity.json`, exactly like any
other distribution: there is no default identity, so forgetting `--identity` is an `argparse`
error, never a silent fallback that ships a distribution branded as Pegasus.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import stat
import sys
import types
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "install.sh"
PACKAGE_SOURCE = ROOT / "src" / "pegasus"

#: The banner line bracketing the identity header block in the template. Exactly two of these
#: must appear in the template: the header lives strictly between the first and the second.
HEADER_BANNER = "# " + "=" * 76

#: One regex per header variable, matching the exact single-quoted assignment line
#: `build_installer.py` replaces. `re.MULTILINE` anchors `^`/`$` to line boundaries so each
#: pattern matches only the assignment itself, never a mention of the variable name elsewhere.
_ASSIGNMENT = {
    name: re.compile(rf"^{name}='.*'$", re.MULTILINE)
    for name in (
        "PRODUCT_ID",
        "PRODUCT_DISPLAY_NAME",
        "PRODUCT_PROGRAM_NAME",
        "PRODUCT_RELEASE_BASE_URL_DEFAULT",
    )
}

#: The two-line intro of `install.sh`'s own usage comment (the one `uso()` prints for
#: `--help`), naming the product and what it installs. Lives above the identity header
#: block -- `--help`'s audience installs the product and does not read the header -- so
#: it cannot reference `PRODUCT_DISPLAY_NAME`/`PRODUCT_PROGRAM_NAME` the way the header
#: itself does; a shell comment cannot expand a variable. Instead this is rendered
#: straight from the identity, the same values the header assignments get, kept public
#: (not "_"-prefixed) so `tests/test_install_identity.py` can import the exact same
#: pattern rather than re-deriving the same shape a second time.
USAGE_INTRO = re.compile(
    r"^# Instala .+ en una cuenta Linux limpia: nvm \+ Node LTS, el CLI que elijas\n"
    r"# y el binario de .+, en ese orden, y deja el resultado listo para trabajar\.$",
    re.MULTILINE,
)

#: The `--bin-dir DIR` line of the same usage comment, which also names the product
#: (by its program name) rather than a generic "the product".
USAGE_BIN_DIR_LINE = re.compile(
    r"^(#   \./install\.sh --bin-dir DIR\s+instala el binario de ).+?( en DIR en vez de ~/\.local/bin)$",
    re.MULTILINE,
)

#: The single-quoted `CLI_CATALOGO=...` assignment: the list of CLI ids and display names
#: this engine ships, as "id:Name" pairs separated by commas -- see the comment above it in
#: the template. Lives just *after* the identity header block (it is engine data, not a
#: distribution's own identity), so it is matched and replaced separately from `_ASSIGNMENT`,
#: which only ever touches the header itself.
CLI_CATALOGO_ASSIGNMENT = re.compile(r"^CLI_CATALOGO='.*'$", re.MULTILINE)

#: The `declare -A CLI_BINARIO=(...)` line: which executable `command -v` should look for, per
#: CLI id -- read from each adapter's own public `binary` attribute (see `_load_adapters_catalog`).
#: A bash associative-array literal, not a single-quoted scalar, so it gets its own pattern
#: rather than reusing `CLI_CATALOGO_ASSIGNMENT`'s shape.
CLI_BINARIO_ASSIGNMENT = re.compile(r"^declare -A CLI_BINARIO=\(.*\)$", re.MULTILINE)


def _load_identity_module(source: Path) -> types.ModuleType:
    """Load `<source>/core/identity.py` as a standalone module, by file path.

    Not `sys.path.insert(0, source.parent); import pegasus.core.identity`: that only works when
    `source` is itself named `pegasus`, and it would silently resolve to whatever `pegasus`
    package is already imported (the real engine under test, when this runs from inside the test
    suite) rather than the one actually being built against. Loading the file directly validates
    against the exact source tree this script is pointed at, regardless of its directory name --
    the same reasoning `tools/build_zipapp.py::_load_identity_module` documents at length.

    This *does* touch `sys.modules`, briefly and on purpose: `identity.py` uses
    `from __future__ import annotations`, so its `@dataclass(frozen=True)` fields are deferred
    string annotations, and `dataclasses._is_type()` resolves them by looking `cls.__module__` up
    in `sys.modules`. Without registering the module there first, `exec_module` raises
    `AttributeError: 'NoneType' object has no attribute '__dict__'` before this function's own
    validation ever runs. The `finally` removes the registration again as soon as `exec_module`
    returns (or raises), so nothing of this transient load lingers in `sys.modules` afterward.
    """
    identity_module_path = source / "core" / "identity.py"
    if not identity_module_path.is_file():
        raise ValueError(
            f"{source} has no core/identity.py; it cannot validate the identity it is asked to build against"
        )
    # Unique per call, not a fixed name: two builds in the same process on different threads must
    # not delete each other's still-running `exec_module` registration out from under it.
    module_name = f"_build_installer_identity_validator_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, identity_module_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"could not load {identity_module_path} to validate identity")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        del sys.modules[module_name]
    return module


def _load_adapters_catalog(package_source: Path) -> tuple[tuple[str, str, str], ...]:
    """`(cli_id, display_name, binary)` for every adapter `<package_source>/adapters/__init__.py`'s
    `available()` registers, in the registry's own (sorted) order.

    `binary` is the adapter's own public `binary` attribute (see `Adapter.binary` on the
    OpenCode and Claude Code adapters) -- the exact executable name that adapter's own
    `detect()` already looks up. It is read here, not hardcoded in `install.sh`, for the same
    reason `display_name` is: which command `command -v` should look for is a fact about the
    adapter, and `install.sh`'s `CLI_BINARIO` map exists only to give the shell side a copy of
    a fact the adapter already owns.

    Unlike `core/identity.py`, `adapters/__init__.py` imports by absolute name --
    `from pegasus.adapters.claudecode import Adapter` -- so it cannot be loaded by bare file
    path the way `_load_identity_module` loads identity: those absolute imports resolve
    against `sys.modules['pegasus']`, not against `package_source`, and loading by path alone
    would leave them resolving to whatever `pegasus` this process already has imported (the
    real engine under test, when this runs from inside the test suite) rather than the tree
    this build was actually pointed at -- exactly the failure mode `_load_identity_module`
    documents at length for its own, simpler case.

    Since the absolute imports are spelled `pegasus.*` literally, the only way to make them
    resolve against `package_source` is to import it AS `pegasus`: this evicts any
    `pegasus`/`pegasus.*` entries already cached in `sys.modules`, adds `package_source`'s
    parent to the front of `sys.path`, imports fresh, and restores both `sys.path` and the
    evicted `sys.modules` entries in a `finally` -- so nothing of this transient import lingers
    afterward, and a build run from inside the test suite still validates against the tree it
    was actually pointed at.
    """
    adapters_init = package_source / "adapters" / "__init__.py"
    if not adapters_init.is_file():
        raise ValueError(f"{package_source} has no adapters/__init__.py; it cannot list supported CLIs")
    if package_source.name != "pegasus":
        raise ValueError(
            f"--package-source must be a directory named 'pegasus' (its adapters import "
            f"'pegasus.adapters...' by absolute name, which only resolves against a tree "
            f"importable as 'pegasus'); got {package_source}"
        )

    parent = str(package_source.parent)
    saved_modules = {
        name: module for name, module in sys.modules.items()
        if name == "pegasus" or name.startswith("pegasus.")
    }
    for name in saved_modules:
        del sys.modules[name]

    sys.path.insert(0, parent)
    try:
        adapters_module = importlib.import_module("pegasus.adapters")
        registry = adapters_module.available()
        catalog = []
        for cli_id in registry.ids():
            adapter = registry.get(cli_id)
            binary = getattr(adapter, "binary", "")
            if not binary:
                raise ValueError(
                    f"adapter {cli_id!r} has no non-empty 'binary' attribute; "
                    f"install.sh's CLI_BINARIO needs it to know what to run `command -v` on"
                )
            catalog.append((cli_id, adapter.display_name, binary))
        return tuple(catalog)
    finally:
        sys.path.remove(parent)
        for name in list(sys.modules):
            if name == "pegasus" or name.startswith("pegasus."):
                del sys.modules[name]
        sys.modules.update(saved_modules)


def _format_cli_catalogo(catalog: tuple[tuple[str, str, str], ...]) -> str:
    """Render `[(cli_id, display_name, binary), ...]` as install.sh's `CLI_CATALOGO` format:
    "id:Name" pairs separated by commas -- see the comment above that assignment in the
    template. A display name is free-form prose (unlike a `cli_id`), so a comma or colon
    inside one would silently corrupt this format on the shell side; caught here, at build
    time, rather than shipping an installer whose CLI menu is quietly wrong.
    """
    for cli_id, display_name, _binary in catalog:
        if "," in display_name or ":" in display_name:
            raise ValueError(
                f"CLI {cli_id!r} display name {display_name!r} contains a ',' or ':', which "
                f"install.sh's CLI_CATALOGO format cannot represent"
            )
    return ",".join(f"{cli_id}:{display_name}" for cli_id, display_name, _binary in catalog)


def _format_cli_binario(catalog: tuple[tuple[str, str, str], ...]) -> str:
    """Render `[(cli_id, display_name, binary), ...]` as install.sh's whole `CLI_BINARIO`
    line: a bash associative-array literal, `declare -A CLI_BINARIO=([id]='binary' ...)`.

    Keeps `CLI_CATALOGO` and `CLI_BINARIO` from ever drifting apart the way a hand-maintained
    `CLI_BINARIO` could: every id the catalog carries gets an entry here from the same
    `catalog` list, in the same build pass -- see `install.sh`'s own `verificar_catalogo_cli`
    for the runtime guard that catches it if an old, un-regenerated `install.sh` ever disagrees
    with a newer `CLI_CATALOGO` anyway.
    """
    pares = " ".join(f"[{cli_id}]='{_quote_single(binary)}'" for cli_id, _display_name, binary in catalog)
    return f"declare -A CLI_BINARIO=({pares})"


def parse_identity(package_source: Path, identity: Path) -> object:
    """Parse and fully validate `identity` with the exact rules the built artifact itself runs.

    Reusing `core/identity.py`'s `parse()` -- rather than re-declaring the wordmark charset and
    length limit here -- is the only way the build-time check and the runtime check can never
    drift apart into two different rules for the same name.
    """
    if not identity.is_file():
        raise ValueError(f"--identity does not exist: {identity}")
    identity_module = _load_identity_module(package_source)
    try:
        return identity_module.parse(identity.read_bytes())
    except identity_module.IdentityError as error:
        raise ValueError(str(error)) from error


def _quote_single(value: str) -> str:
    """POSIX single-quote a value for a shell assignment: close the quote, escape a literal
    single quote outside of quoting, reopen -- the same rule `install.sh`'s own
    `escapar_comilla_simple_posix` applies to `--bin-dir`. `identity.display_name` and
    `identity.program_name` are only checked for non-emptiness by `core/identity.py` (unlike
    `wordmark_words`, which is charset-restricted), so a value carrying a single quote must still
    produce a syntactically valid assignment rather than a shell script that fails to parse.
    """
    return value.replace("'", "'\\''")


def render(template_text: str, identity: object, package_source: Path) -> str:
    """Replace the four identity header assignments in `template_text`, leaving every other
    character of the template untouched.

    `PRODUCT_RELEASE_BASE_URL_DEFAULT` comes straight from
    `identity.release.install_base_url_default` -- not derived by splitting `release_page_url` or
    `asset_url_template`. `core/identity.py`'s own `ReleaseSource` docstring explains why that
    field is required rather than derived: not every release host shapes its "latest" download URL
    the way GitHub does, and even for GitHub itself `releases/latest/download/<asset>` and
    `releases/download/latest/<asset>` are different paths, so `asset_url_template` could not
    produce it either way.

    `CLI_CATALOGO` and `CLI_BINARIO`, unlike the four values above, are not distribution
    identity at all -- they are engine data (which CLIs `package_source`'s own
    `pegasus.adapters.available()` ships, and what each one's own `binary` attribute says to
    run `command -v` on), the same for Pegasus's own build as for any other distribution built
    off the same engine. Both still get replaced on every build rather than left as whatever
    the template happened to carry, so a third adapter shows up in both the day it registers
    rather than when someone remembers to hand-edit `install.sh`.
    """
    values = {
        "PRODUCT_ID": identity.product_id,
        "PRODUCT_DISPLAY_NAME": identity.display_name,
        "PRODUCT_PROGRAM_NAME": identity.program_name,
        "PRODUCT_RELEASE_BASE_URL_DEFAULT": identity.release.install_base_url_default,
    }

    banners = template_text.count(HEADER_BANNER)
    if banners != 2:
        raise ValueError(
            f"template must have exactly two {HEADER_BANNER!r} banner lines delimiting the "
            f"identity header block, found {banners}"
        )
    before, header, after = template_text.split(HEADER_BANNER)

    if not USAGE_INTRO.search(before):
        raise ValueError("template's usage comment has no product-naming intro paragraph to replace")
    before = USAGE_INTRO.sub(
        lambda match: (
            f"# Instala {identity.display_name} en una cuenta Linux limpia: nvm + Node LTS, el CLI que elijas\n"
            f"# y el binario de {identity.program_name}, en ese orden, y deja el resultado listo para trabajar."
        ),
        before,
        count=1,
    )
    if not USAGE_BIN_DIR_LINE.search(before):
        raise ValueError("template's usage comment has no --bin-dir line naming the product to replace")
    before = USAGE_BIN_DIR_LINE.sub(
        lambda match: match.group(1) + identity.program_name + match.group(2), before, count=1
    )

    replaced = header
    for name, value in values.items():
        pattern = _ASSIGNMENT[name]
        if not pattern.search(replaced):
            raise ValueError(f"template's identity header has no {name}=... assignment to replace")
        replaced = pattern.sub(f"{name}='{_quote_single(value)}'", replaced, count=1)

    catalog = _load_adapters_catalog(package_source)

    if not CLI_CATALOGO_ASSIGNMENT.search(after):
        raise ValueError("template has no CLI_CATALOGO=... assignment to replace")
    catalogo = _format_cli_catalogo(catalog)
    after = CLI_CATALOGO_ASSIGNMENT.sub(f"CLI_CATALOGO='{_quote_single(catalogo)}'", after, count=1)

    if not CLI_BINARIO_ASSIGNMENT.search(after):
        raise ValueError("template has no declare -A CLI_BINARIO=... assignment to replace")
    binario_linea = _format_cli_binario(catalog)
    after = CLI_BINARIO_ASSIGNMENT.sub(lambda match: binario_linea, after, count=1)

    return before + HEADER_BANNER + replaced + HEADER_BANNER + after


def build(template: Path, identity_path: Path, package_source: Path, output: Path) -> None:
    identity = parse_identity(package_source, identity_path)
    template_text = template.read_text(encoding="utf-8")
    rendered = render(template_text, identity, package_source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    mode = output.stat().st_mode
    output.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--template", type=Path, default=TEMPLATE, help="the install.sh template to fill in")
    parser.add_argument(
        "--package-source", type=Path, default=PACKAGE_SOURCE,
        help="a pegasus package tree providing core/identity.py, used only to validate --identity",
    )
    parser.add_argument("--identity", type=Path, required=True, help="identity.json to build the installer from")
    parser.add_argument("--out", type=Path, required=True, help="where to write the generated install.sh")
    arguments = parser.parse_args()

    if not arguments.template.is_file():
        parser.error(f"--template does not exist: {arguments.template}")
    if arguments.out.exists():
        parser.error(f"--out must not already exist: {arguments.out}")

    try:
        build(arguments.template, arguments.identity, arguments.package_source, arguments.out)
    except ValueError as error:
        parser.error(str(error))

    print(f"WROTE installer: {arguments.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
