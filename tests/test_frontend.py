"""Front-end register plan — no board required."""

from sevenbeing_ads1299.frontend import apply_frontend, parse_frontend
from sevenbeing_ads1299.registers import chset


class _Rec:
    def __init__(self) -> None:
        self.writes: list[tuple[str, int]] = []

    def write_register(self, name: str, value: int) -> None:
        self.writes.append((name, value))


def test_shared_ch1_ch2_plan():
    cfg = parse_frontend(
        {"channels": [1, 2], "reference": "shared", "bias": True, "gain": 24}
    )
    dev = _Rec()
    summary = apply_frontend(dev, cfg)
    got = dict(dev.writes)
    assert got["ch1set"] == chset(gain=24, mux="normal", pd=False)
    assert got["ch2set"] == chset(gain=24, mux="normal", pd=False)
    assert got["ch3set"] == chset(gain=24, mux="normal", pd=True)
    assert got["ch8set"] == chset(gain=24, mux="normal", pd=True)
    assert got["misc1"] == 0x20
    assert got["config3"] & 0x0C == 0x0C
    assert got["biassensp"] == 0x03
    assert got["biassensn"] == 0x00
    assert "CH1 CH2" in summary
    assert "SRB1" in summary


def test_differential_turns_srb_off():
    cfg = parse_frontend({"channels": [1], "reference": "differential", "bias": False, "gain": 1})
    dev = _Rec()
    apply_frontend(dev, cfg)
    got = dict(dev.writes)
    assert got["misc1"] == 0x00
    assert got["biassensp"] == 0x00
    assert got["config3"] & 0x0C == 0x00
    assert got["ch1set"] == chset(gain=1, mux="normal", pd=False)
