"""USB scan mapping — no board required."""

from __future__ import annotations

import pytest

pytest.importorskip("sevenbeing")

from sevenbeing.devices.base import DeviceKind

from sevenbeing_ads1299.driver import Ads1299Driver
from sevenbeing_ads1299.usb_ids import BOOT_PID, BOOT_VID, STYX_PID


class _Usb:
    def __init__(self, pid: int, bus: int, address: int) -> None:
        self.idVendor = BOOT_VID
        self.idProduct = pid
        self.bus = bus
        self.address = address


def test_scan_empty(monkeypatch):
    import sevenbeing_ads1299.driver as drv

    monkeypatch.setattr(drv, "_iter_mmb0", lambda: iter(()))
    assert Ads1299Driver().scan() == []


def test_scan_boot_and_styx(monkeypatch):
    import sevenbeing_ads1299.driver as drv

    devices = [_Usb(BOOT_PID, 1, 4), _Usb(STYX_PID, 1, 5)]
    monkeypatch.setattr(drv, "_iter_mmb0", lambda: iter(devices))
    found = Ads1299Driver().scan()
    assert [d.id for d in found] == ["ads1299:001:004", "ads1299:001:005"]
    assert found[0].kind == DeviceKind.ADS1299
    assert found[0].meta["state"] == "boot"
    assert found[1].meta["state"] == "styx"
    assert found[1].n_channels == 8
    assert found[1].channels[0] == "CH1"
    assert found[1].address == f"{BOOT_VID:04x}:{STYX_PID:04x}"
