"""Optional Rust accel (PyO3). Falls back silently if the extension is not built.

Build:
  cd native && maturin develop --release
"""

from __future__ import annotations

from typing import Any

_native: Any = None
_tried = False


def load() -> Any | None:
    global _native, _tried
    if _tried:
        return _native
    _tried = True
    try:
        import sevenbeing_ads1299_native as n  # type: ignore

        _native = n
    except Exception:
        _native = None
    return _native


def has_native() -> bool:
    return load() is not None


def decode_styx_codes(buf: bytes) -> bytes | None:
    """Little-endian i32 codes, 8 per frame. None if the extension is missing."""
    n = load()
    if n is None:
        return None
    raw = n.decode_styx_codes(buf)
    return raw if isinstance(raw, bytes) else bytes(raw)


def decode_styx_uv(buf: bytes, vref: float, gain: float) -> bytes | None:
    """Little-endian f64 microvolts, 8 per frame. None if the extension is missing."""
    n = load()
    if n is None:
        return None
    raw = n.decode_styx_uv(buf, float(vref), float(gain))
    return raw if isinstance(raw, bytes) else bytes(raw)
