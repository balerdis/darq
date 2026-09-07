"""Pure transform logic for rebranding an extracted pegasus package tree into DARQ's own.

Everything here is a pure function over strings, paths and the parsed ``rebrand.json`` map: no
filesystem access, no network. The one function that touches a real directory on disk,
``apply_to_tree``, is a thin edge that only ever calls the pure functions below and never contains
transform logic of its own -- see that function's own docstring.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_PLACEHOLDER_TEMPLATE = "\x00DARQ_PROTECTED_{index}\x00"
"""A NUL-delimited marker, chosen because it can never occur in real markdown/text prose and
because it is trivially removable if a mask is ever left unrestored by a bug -- unlike a
human-readable placeholder, it can never be mistaken for real substituted content."""


@dataclass(frozen=True)
class RebrandMap:
    """The parsed, immutable contents of ``rebrand.json``.

    ``protected_tokens`` is stored pre-sorted longest-first: masking and unmasking both walk it in
    this order so a token that is itself a prefix of a longer one (``.pegasus-`` inside
    ``.pegasus-data``) is never masked in a way that clips the longer token out from under it.
    """

    renames: tuple[tuple[str, str], ...]
    substitutions: tuple[tuple[str, str], ...]
    protected_tokens: tuple[str, ...]
    excluded_paths: tuple[str, ...]
    substitution_extensions: tuple[str, ...] = (".md", ".txt")

    @property
    def rename_map(self) -> dict[str, str]:
        return dict(self.renames)


def load_map(path: Path) -> RebrandMap:
    """Parse ``rebrand.json`` into a :class:`RebrandMap`. The only I/O in this function is the
    single read of ``path`` itself; everything else is pure construction."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_map(payload)


def parse_map(payload: dict) -> RebrandMap:
    renames = tuple((entry["from"], entry["to"]) for entry in payload["renames"])
    substitutions = tuple((pair[0], pair[1]) for pair in payload["substitutions"])
    protected = tuple(sorted(payload["protected_tokens"], key=len, reverse=True))
    excluded = tuple(payload.get("excluded_paths", ()))
    return RebrandMap(
        renames=renames,
        substitutions=substitutions,
        protected_tokens=protected,
        excluded_paths=excluded,
    )


def mask(text: str, protected_tokens: tuple[str, ...]) -> str:
    """Replace every occurrence of a protected token with an opaque, order-indexed placeholder.

    ``protected_tokens`` must already be sorted longest-first (``RebrandMap`` guarantees this on
    construction) -- masking a shorter token before a longer one that contains it would replace
    part of the longer token and leave the rest behind as literal, unmasked text.
    """
    for index, token in enumerate(protected_tokens):
        text = text.replace(token, _PLACEHOLDER_TEMPLATE.format(index=index))
    return text


def unmask(text: str, protected_tokens: tuple[str, ...]) -> str:
    """The inverse of :func:`mask`: restore every placeholder to its original protected token."""
    for index, token in enumerate(protected_tokens):
        text = text.replace(_PLACEHOLDER_TEMPLATE.format(index=index), token)
    return text


def substitute_body(text: str, rebrand_map: RebrandMap) -> str:
    """Apply every body substitution rule, in declared order, with protected tokens masked out
    for the duration.

    Order is correctness-critical and is never re-derived here: ``rebrand_map.substitutions`` is
    applied exactly in the order ``rebrand.json`` declares it, longest-match-first, so
    ``king-pegasus`` becomes ``arquitecto-darq`` as a whole before the later, bare ``pegasus`` rule
    ever sees it -- see ``tests/test_rebrand.py::test_king_pegasus_never_degrades``.
    """
    masked = mask(text, rebrand_map.protected_tokens)
    for old, new in rebrand_map.substitutions:
        masked = masked.replace(old, new)
    return unmask(masked, rebrand_map.protected_tokens)


def rename_relative_path(relative_posix: str, rebrand_map: RebrandMap) -> str:
    """The path a file should be written to, relative to the content root.

    Only the four explicitly declared renames in ``rebrand.json`` change a path; every other file
    keeps its own relative path unchanged. This is a lookup, not a general filename transform --
    the engine's content tree today has exactly four filenames containing ``pegasus``, and all four
    are declared explicitly, so there is nothing left for a heuristic rule to guess at.
    """
    return rebrand_map.rename_map.get(relative_posix, relative_posix)


def is_excluded(relative_posix: str, rebrand_map: RebrandMap) -> bool:
    """Whether a path must never be read or rewritten by the transform, regardless of extension."""
    name = relative_posix.rsplit("/", 1)[-1]
    return relative_posix in rebrand_map.excluded_paths or name in rebrand_map.excluded_paths


def should_substitute_body(relative_posix: str, rebrand_map: RebrandMap) -> bool:
    """Whether a file's body is a candidate for substitution: right extension, not excluded.

    Deliberately extension-gated rather than content-sniffed: ``.json`` files (in particular
    ``content/mcp/playwright-package-lock.json``, which pins a real npm root package name the
    engine itself synthesized) are never substituted, by design -- see ``rebrand.json``'s
    ``accepted_residue`` entry.
    """
    if is_excluded(relative_posix, rebrand_map):
        return False
    return any(relative_posix.endswith(extension) for extension in rebrand_map.substitution_extensions)


def apply_to_tree(content_root: Path, rebrand_map: RebrandMap) -> None:
    """Apply the rebrand transform to every file under ``content_root``, in place.

    The only I/O in this module: walk every file once, decide (via the pure functions above)
    whether its body is substituted and whether its path is renamed, then write it back. Renames
    are resolved before any file is written, so a rename target that itself needs its body
    substituted still gets both -- new content at the new path, nothing left behind at the old one.
    """
    files = sorted(path for path in content_root.rglob("*") if path.is_file())
    for path in files:
        relative_posix = path.relative_to(content_root).as_posix()
        if is_excluded(relative_posix, rebrand_map):
            continue
        target_relative = rename_relative_path(relative_posix, rebrand_map)
        target_path = content_root / target_relative
        if should_substitute_body(relative_posix, rebrand_map):
            text = path.read_text(encoding="utf-8")
            new_text = substitute_body(text, rebrand_map)
            if target_path != path:
                path.unlink()
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(new_text, encoding="utf-8")
        elif target_path != path:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            path.replace(target_path)
