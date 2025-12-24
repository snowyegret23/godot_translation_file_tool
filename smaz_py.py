"""Pure-Python Smaz decompressor fallback.

This module provides a `decompress(bytes) -> str` function compatible
with the C extension's interface used by this project. It lazily
fetches the official `Smaz_rcb` codebook from the upstream GitHub
`antirez/smaz` repository when needed.

If network access is unavailable, decompression will raise a RuntimeError
with instructions to install the native `smaz` package.
"""

from __future__ import annotations

import re
from typing import List, Optional

_RCB: Optional[List[str]] = None


def _fetch_rcb() -> List[str]:
    """Download and parse Smaz_rcb from upstream smaz.c on GitHub."""
    import urllib.request

    url = "https://raw.githubusercontent.com/antirez/smaz/master/smaz.c"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            txt = resp.read().decode("latin1")
    except Exception as e:
        raise RuntimeError(
            "Unable to fetch smaz codebook from the internet. "
            "Install the native 'smaz' package (pip install smaz) or ensure network access."
        ) from e

    m = re.search(r"static\s+char\s+\*Smaz_rcb\[\d+\]\s*=\s*\{(.*?)\};", txt, re.S)
    if not m:
        raise RuntimeError("Couldn't locate Smaz_rcb in upstream smaz.c")

    inner = m.group(1)
    # Extract double-quoted C strings inside the initializer
    raw_items = re.findall(r'"(.*?)"', inner, re.S)

    def _decode_c_string(s: str) -> str:
        # Convert octal escapes (e.g. \003) to \xNN then use unicode_escape
        s2 = re.sub(r"\\([0-7]{1,3})", lambda mo: "\\x%02x" % int(mo.group(1), 8), s)
        try:
            return bytes(s2, "utf-8").decode("unicode_escape")
        except Exception:
            # Best effort fallback
            return s2

    return [_decode_c_string(s) for s in raw_items]


def _ensure_rcb() -> None:
    global _RCB
    if _RCB is not None:
        return
    _RCB = _fetch_rcb()


def decompress(b: bytes) -> str:
    """Decompress bytes compressed with smaz and return a UTF-8 str.

    The function mirrors the behavior of the C extension: bytes input,
    string output. If the codebook cannot be obtained and decompression
    is required, a RuntimeError is raised.
    """
    if not b:
        return ""
    if _RCB is None:
        _ensure_rcb()
    assert _RCB is not None

    out = bytearray()
    i = 0
    n = len(b)
    while i < n:
        c = b[i]
        if c == 254:  # verbatim single byte
            if i + 1 >= n:
                break
            out.append(b[i + 1])
            i += 2
        elif c == 255:  # verbatim string
            if i + 1 >= n:
                break
            length = b[i + 1] + 1
            start = i + 2
            end = start + length
            out.extend(b[start:end])
            i = end
        else:
            try:
                s = _RCB[c]
            except Exception:
                # Safety: if index out of range, stop
                break
            # s is a Python string; encode as utf-8 bytes
            out.extend(s.encode("utf-8"))
            i += 1

    # Return as text. Use replacement to avoid decode errors.
    return out.decode("utf-8", errors="replace")


def compress(data: bytes) -> bytes:
    """Compress not implemented in pure-Python fallback.

    The project's use-case writes uncompressed strings when saving, so
    compression is not required. If an actual compressor is required,
    install the `smaz` package.
    """
    raise NotImplementedError("compress() is not implemented in the pure-Python fallback; install 'smaz-py3' for a full implementation")
