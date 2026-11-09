"""ADS1299 electrode front-end: which inputs are on, shared reference, bias."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .presets import pack_config3
from .registers import chset

GAINS = (1, 2, 4, 6, 8, 12, 24)
REFERENCES = ("shared", "differential")


@dataclass(frozen=True)
class FrontEndConfig:
    """How the header pins map onto the converter.

    ``shared`` turns on SRB1 so every enabled channel's − pin is the SRB1
    electrode. Wire signals to INxP, the reference to SRB1, and bias to BIAS.
    ``differential`` leaves SRB1 off: each channel uses its own + and −.
    """

    channels: tuple[int, ...] = (1, 2)
    reference: str = "shared"
    bias: bool = True
    gain: int = 24

    def summary(self) -> str:
        names = " ".join(f"CH{n}" for n in self.channels)
        ref = "อ้างอิงร่วม SRB1" if self.reference == "shared" else "ดิฟเฟอเรนเชียล"
        bias = "BIAS" if self.bias else "ไม่มี BIAS"
        return f"{names} · {ref} · {bias} · gain {self.gain:g}"

    def to_dict(self) -> dict:
        return {
            "channels": list(self.channels),
            "reference": self.reference,
            "bias": self.bias,
            "gain": self.gain,
        }


def parse_frontend(payload: dict | str | None) -> FrontEndConfig:
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            raise ValueError("empty front-end config")
        raw = json.loads(text)
    elif isinstance(payload, dict):
        raw = payload
    else:
        raise ValueError("front-end config must be an object")
    if not isinstance(raw, dict):
        raise ValueError("front-end config must be an object")

    channels_in = raw.get("channels", [1, 2])
    if isinstance(channels_in, str):
        channels_in = [part for part in channels_in.replace(",", " ").split() if part]
    picked: list[int] = []
    for item in channels_in:
        n = int(item)
        if n < 1 or n > 8:
            raise ValueError(f"channel {n} is outside CH1–CH8")
        if n not in picked:
            picked.append(n)
    if not picked:
        raise ValueError("pick at least one channel")

    reference = str(raw.get("reference") or "shared").strip().lower()
    if reference not in REFERENCES:
        raise ValueError("reference must be shared or differential")

    gain = int(raw.get("gain") if raw.get("gain") is not None else 24)
    if gain not in GAINS:
        raise ValueError(f"gain must be one of {GAINS}")

    bias = raw.get("bias", True)
    if isinstance(bias, str):
        bias = bias.strip().lower() not in {"0", "false", "off", "no"}

    return FrontEndConfig(
        channels=tuple(picked),
        reference=reference,
        bias=bool(bias),
        gain=gain,
    )


def config_from_meta(meta: dict | None) -> FrontEndConfig | None:
    if not meta:
        return None
    raw = meta.get("frontend")
    if raw in (None, ""):
        return None
    return parse_frontend(raw)


def apply_frontend(dev, cfg: FrontEndConfig) -> str:
    """Write CHnSET / MISC1 / CONFIG3 / BIAS sense. Safe only between acquires."""
    enabled = set(cfg.channels)
    for n in range(1, 9):
        dev.write_register(
            f"ch{n}set",
            chset(gain=cfg.gain, mux="normal", pd=n not in enabled),
        )
    dev.write_register("misc1", 0x20 if cfg.reference == "shared" else 0x00)
    dev.write_register(
        "config3",
        pack_config3(pd_refbuf=True, biasref_int=cfg.bias, pd_bias=cfg.bias),
    )
    mask = 0
    if cfg.bias:
        for n in enabled:
            mask |= 1 << (n - 1)
    dev.write_register("biassensp", mask)
    dev.write_register("biassensn", 0x00)
    return cfg.summary()
