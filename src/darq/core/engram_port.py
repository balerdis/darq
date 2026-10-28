"""Which port this OS user's engram integrations talk to.

engram's HTTP server listens on 127.0.0.1:7437 and that port is shared by every
OS user of the machine: if user A's `engram serve` holds it, the engram plugin or hook
of user B's CLI would send B's sessions and prompts into A's database. The
resolution below is implemented three times -- here (used by `doctor`), in the
engram plugin of one adapter (TypeScript) and in the engram hook of another
(a standalone stdlib script) -- and a parity test feeds the same
synthetic /proc tables to all three:

* ``ENGRAM_PORT`` set to a valid port: that port, or nothing when only another
  uid listens on it (the person chose it, so there is no fallback);
* otherwise 7437 when nobody or this uid listens on it;
* otherwise the per-user port ``17437 + uid % 10000`` (17437-27436, below the
  Linux ephemeral range), under the same rule: free or own, else nothing. It is
  derived, not reserved: two uids 10000 apart collide, and then it fails closed;
* without ``/proc/net/tcp`` it cannot tell, so it behaves as before: the
  explicit port or 7437.

"Nothing" means: send no request, start no server.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from darq.core import listeners

#: Test seams: where the IPv4 and IPv6 tables are read from instead of /proc.
#: The plugin and the hook honor the same two names.
TCP4_ENV = "ENGRAM_PORT_PROC_TCP4"
TCP6_ENV = "ENGRAM_PORT_PROC_TCP6"

DEFAULT_PORT = 7437
FALLBACK_BASE = 17437
FALLBACK_SPAN = 10000
#: Test seam: replaces ``FALLBACK_BASE`` so a test never binds a port another
#: run (or user) may hold. Honored by the three implementations alike.
FALLBACK_BASE_ENV = "ENGRAM_PORT_FALLBACK_BASE"
_PORT_TEXT = re.compile(r"[0-9]{1,5}")


def fallback_port(uid: int, environment: Mapping[str, str] | None = None) -> int:
    base = FALLBACK_BASE
    raw = (environment or {}).get(FALLBACK_BASE_ENV, "").strip()
    if _PORT_TEXT.fullmatch(raw) and 1 <= int(raw) and int(raw) + uid % FALLBACK_SPAN <= 65535:
        base = int(raw)
    return base + uid % FALLBACK_SPAN


def explicit_port(environment: Mapping[str, str]) -> int | None:
    """``ENGRAM_PORT`` when it is a valid port, else ``None`` (an unusable value counts as unset)."""
    raw = environment.get("ENGRAM_PORT", "").strip()
    if not _PORT_TEXT.fullmatch(raw):
        return None
    value = int(raw)
    return value if 1 <= value <= 65535 else None


@dataclass(frozen=True)
class Resolution:
    #: The port to use, or ``None`` when every candidate is held by another uid.
    port: int | None
    #: The port that was refused, and who holds it (empty when nothing was refused).
    blocked_port: int | None = None
    blocked_uids: tuple[int, ...] = ()
    explicit: bool = False


def resolve(
    environment: Mapping[str, str],
    uid: int,
    *,
    tcp4: Path = listeners.TCP4,
    tcp6: Path = listeners.TCP6,
) -> Resolution:
    explicit = explicit_port(environment)
    if not tcp4.is_file():
        return Resolution(explicit if explicit is not None else DEFAULT_PORT, explicit=explicit is not None)

    def holders(port: int) -> set[int]:
        return listeners.loopback_holders(port, tcp4, tcp6)

    def usable(port: int) -> bool:
        held = holders(port)
        return not held or uid in held

    if explicit is not None:
        if usable(explicit):
            return Resolution(explicit, explicit=True)
        return Resolution(None, explicit, tuple(sorted(holders(explicit))), explicit=True)
    if usable(DEFAULT_PORT):
        return Resolution(DEFAULT_PORT)
    refused = tuple(sorted(holders(DEFAULT_PORT)))
    fallback = fallback_port(uid, environment)
    if usable(fallback):
        return Resolution(fallback, DEFAULT_PORT, refused)
    return Resolution(None, DEFAULT_PORT, refused)


def proc_paths(environment: Mapping[str, str]) -> tuple[Path, Path]:
    return (
        Path(environment.get(TCP4_ENV) or listeners.TCP4),
        Path(environment.get(TCP6_ENV) or listeners.TCP6),
    )


def warning(resolution: Resolution, uid: int, environment: Mapping[str, str] | None = None) -> str | None:
    """What `doctor` says when another OS user holds the port, or ``None`` when nothing is wrong."""
    if resolution.blocked_port is None:
        return None
    owners = ", ".join(str(owner) for owner in resolution.blocked_uids)
    held = (
        f"port {resolution.blocked_port} on 127.0.0.1 is held by a process of another OS user "
        f"(uid {owners}), most likely that user's `engram serve`, so sharing it would send this "
        f"user's sessions and prompts into that user's memory."
    )
    if resolution.port is not None and resolution.port != resolution.blocked_port:
        return (
            f"{held} The engram integrations of the supported CLIs "
            f"will use port {resolution.port} instead, derived from this user's uid, and start "
            f"their own `engram serve` there."
        )
    if resolution.explicit:
        return (
            f"{held} ENGRAM_PORT points at it, so they will not use another port: engram memory "
            f"is disabled until you set ENGRAM_PORT to a free port."
        )
    return (
        f"{held} The port derived from this user's uid ({fallback_port(uid, environment)}) is held by another OS user "
        f"too (uids 10000 apart share it): engram memory is disabled until you set ENGRAM_PORT to a free port."
    )
