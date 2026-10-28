"""Who listens on a loopback TCP port, read from ``/proc/net/tcp{,6}``.

DARQ officially supports Linux only, where those tables name the OS user
(uid) behind every socket. Two checks share this lookup: the service-port
warning of `doctor` and the engram port resolution (`core/engram_port.py`).
Every way of not knowing -- no /proc, an unreadable or corrupt table -- answers
"nobody", and the callers decide what an unknown means (both fail open).
"""
from __future__ import annotations

import re
from pathlib import Path

TCP4 = Path("/proc/net/tcp")
TCP6 = Path("/proc/net/tcp6")
_HEX_PORT = re.compile(r"[0-9a-fA-F]{1,8}")
_UID = re.compile(r"[0-9]{1,10}")
LISTEN = "0A"
#: Addresses whose listener blocks a bind on 127.0.0.1, as /proc prints them
#: (little-endian words, so 127.0.0.1 is 0100007F): loopback itself, and the
#: wildcard of a service told to listen on every interface.
LOOPBACK_V4 = ("0100007F", "00000000")
LOOPBACK_V6 = (
    "00000000000000000000000001000000",
    "0000000000000000FFFF00000100007F",
    "00000000000000000000000000000000",
    "0000000000000000FFFF000000000000",
)


def listener_uids(path: Path, port: int, loopbacks: tuple[str, ...]) -> set[int]:
    """The uids of the sockets LISTENing on ``port`` at one of ``loopbacks`` in the table ``path``."""
    try:
        lines = path.read_text(encoding="ascii", errors="replace").splitlines()
    except OSError:
        return set()
    uids: set[int] = set()
    for line in lines[1:]:
        fields = line.split()
        if len(fields) < 8 or fields[3] != LISTEN:
            continue
        address, _, hexport = fields[1].partition(":")
        if address.upper() not in loopbacks:
            continue
        # Strict like the other two copies: int() alone would take "+5" or "1_0".
        if not _HEX_PORT.fullmatch(hexport) or not _UID.fullmatch(fields[7]):
            continue
        if int(hexport, 16) == port:
            uids.add(int(fields[7]))
    return uids


def loopback_holders(port: int, tcp4: Path = TCP4, tcp6: Path = TCP6) -> set[int]:
    """Every uid listening on ``port`` over IPv4 or IPv6 loopback (or the wildcard)."""
    return listener_uids(tcp4, port, LOOPBACK_V4) | listener_uids(tcp6, port, LOOPBACK_V6)
