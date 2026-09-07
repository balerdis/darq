"""The DARQ rebrand transform: turns a pinned, extracted pegasus package tree into DARQ's own.

Pure string/path logic lives in ``rebrand.transform``; the only I/O this package performs is at
the edges, in ``transform.apply_to_tree``, which walks a real directory on disk.
"""
