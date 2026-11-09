"""ADS1299EEG-FE on MMB0 — USBStyx driver for sevenbeing.

Stock DSP firmware is buffer-then-USB. The live loop captures the next
block while the previous one is played out. Playback is stretched just
past the measured capture time so the USB re-arm does not open a hole
in the trace.
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from dataclasses import dataclass, field

from sevenbeing.devices.base import DeviceCallbacks, DeviceInfo, DeviceKind
from sevenbeing.devices.montage import Montage

from .data import N_CH, codes_to_volts
from .device import ADS1299
from .frontend import FrontEndConfig, apply_frontend, config_from_meta, parse_frontend
from .stream import iter_blocks
from .usb_ids import BOOT_PID, BOOT_VID, STYX_PID, STYX_VID

# 8 differential inputs. Labels are board channels (CH1–CH8), not a fixed cap.
DEFAULT_MONTAGE = Montage.for_count(
    N_CH,
    labels=tuple(f"CH{i}" for i in range(1, N_CH + 1)),
    sample_rate_hz=250,
)

# 4 s at 250 SPS. Long enough that USB setup is a small fraction of the block,
# short enough that the first samples are not minutes away.
LIVE_CHUNK_FRAMES = 1000

_GAIN_FROM_BITS = {0: 1, 1: 2, 2: 4, 3: 6, 4: 8, 5: 12, 6: 24}


def _device_id(bus: int, address: int) -> str:
    return f"{DeviceKind.ADS1299.value}:{int(bus):03d}:{int(address):03d}"


def _firmware_hint() -> str:
    return os.environ.get("ADS1299_FIRMWARE", "").strip()


def _iter_mmb0():
    """Yield pyusb devices in bootloader or USBStyx. Empty if libusb is missing."""
    try:
        import usb.core
    except ImportError:
        return
    try:
        found = usb.core.find(find_all=True, idVendor=BOOT_VID) or []
    except Exception:
        return
    for dev in found:
        try:
            pid = int(dev.idProduct)
        except Exception:
            continue
        if pid in (STYX_PID, BOOT_PID):
            yield dev


class Ads1299Driver:
    kind = DeviceKind.ADS1299

    def scan(self, timeout: float = 5.0) -> list[DeviceInfo]:
        _ = timeout  # USB enumeration is immediate; BLE-style waits do not apply.
        out: list[DeviceInfo] = []
        seen: set[str] = set()
        firmware = _firmware_hint()
        for dev in _iter_mmb0():
            try:
                bus = int(dev.bus)
                address = int(dev.address)
                pid = int(dev.idProduct)
            except Exception:
                continue
            did = _device_id(bus, address)
            if did in seen:
                continue
            seen.add(did)
            styx = pid == STYX_PID
            out.append(
                DeviceInfo(
                    id=did,
                    kind=self.kind,
                    name="ADS1299 MMB0" if styx else "ADS1299 MMB0 (bootloader)",
                    address=f"{BOOT_VID:04x}:{pid:04x}",
                    n_channels=DEFAULT_MONTAGE.n_channels,
                    channels=DEFAULT_MONTAGE.channels,
                    sample_rate_hz=DEFAULT_MONTAGE.sample_rate_hz,
                    meta={
                        "state": "styx" if styx else "boot",
                        "bus": bus,
                        "address": address,
                        "firmware": firmware,
                    },
                )
            )
        return out

    def connect(self, info: DeviceInfo, callbacks: DeviceCallbacks) -> "Ads1299LiveDevice":
        live = Ads1299LiveDevice(info=info, callbacks=callbacks)
        live.start()
        return live


@dataclass
class Ads1299LiveDevice:
    info: DeviceInfo
    callbacks: DeviceCallbacks
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)
    _dev: ADS1299 | None = field(default=None, init=False, repr=False)
    _connected: bool = field(default=False, init=False)
    _sample_rate: int = field(default_factory=lambda: DEFAULT_MONTAGE.sample_rate_hz)
    _detail: str = field(default="", init=False)
    _gain: float = field(default=24.0, init=False)
    _frontend: FrontEndConfig | None = field(default=None, init=False)
    _pending: FrontEndConfig | None = field(default=None, init=False)
    _cfg_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _cfg_gen: int = field(default=0, init=False)
    _applied_gen: int = field(default=0, init=False)
    _last_acquire_s: float = field(default=0.0, init=False)

    @property
    def connected(self) -> bool:
        return self._connected and not self._stop.is_set()

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def n_channels(self) -> int:
        return self.info.n_channels

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name=f"ads1299-{self.info.id}"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=15.0)
        dev = self._dev
        self._dev = None
        if dev is not None:
            try:
                dev.close()
            except Exception:
                pass
        self._connected = False

    def public_state(self) -> dict:
        return {
            **self.info.to_public(),
            "connected": self.connected,
            "sample_rate": self._sample_rate,
            "n_channels": self.n_channels,
            "channels": list(self.info.channels),
            "detail": self._detail,
            "battery": None,
            "locked": self.connected,
            "gain": self._gain,
            "frontend": None if self._frontend is None else self._frontend.to_dict(),
        }

    def configure(self, payload: dict | str) -> str:
        """Queue a front-end write and wait until the stream thread applies it."""
        cfg = parse_frontend(payload)
        with self._cfg_lock:
            self._cfg_gen += 1
            gen = self._cfg_gen
            self._pending = cfg
            self._frontend = cfg
        if isinstance(self.info.meta, dict):
            self.info.meta["frontend"] = json.dumps(cfg.to_dict())
        deadline = time.monotonic() + 12.0
        while time.monotonic() < deadline:
            with self._cfg_lock:
                if self._applied_gen >= gen:
                    return cfg.summary()
            time.sleep(0.05)
        raise TimeoutError("front-end config was not written to the ADS1299")

    def _take_pending(self) -> tuple[FrontEndConfig | None, int]:
        with self._cfg_lock:
            cfg = self._pending
            gen = self._cfg_gen
            self._pending = None
            return cfg, gen

    def _apply_frontend(self, dev: ADS1299, cfg: FrontEndConfig, gen: int) -> None:
        summary = apply_frontend(dev, cfg)
        self._frontend = cfg
        self._gain = float(cfg.gain)
        self._detail = summary
        with self._cfg_lock:
            if gen == self._cfg_gen:
                self._applied_gen = gen
        self._status(summary)

    def _status(self, text: str, warn: bool = False) -> None:
        if self.callbacks.on_status:
            self.callbacks.on_status(self.info.id, text, warn)

    def _pace_period(self, n: int) -> float:
        """Seconds between samples.

        Nominal is 1/sample_rate. USB re-arm makes each capture a little
        longer than that, so play the block over the measured capture time
        plus a small margin. The next block is then already queued.
        """
        nominal = 1.0 / float(max(self._sample_rate, 1))
        acquire_s = self._last_acquire_s
        if n <= 0 or acquire_s <= 0:
            return nominal
        return max(nominal, (acquire_s + 0.08) / float(n))

    def _emit_paced(self, block) -> None:
        """Hand samples to the UI steadily instead of one USB burst.

        Scale with the gain that was active while this block was captured.
        A later register write must not reinterpret those codes.
        """
        handler = self.callbacks.on_sample
        if handler is None or len(block.volts) == 0:
            return
        if getattr(block, "unit", "V") == "uV":
            uv = block.volts
        else:
            gain = float(getattr(block, "capture_gain", self._gain) or self._gain)
            uv = codes_to_volts(block.codes, gain=gain) * 1e6
        period = self._pace_period(len(uv))
        start = time.perf_counter()
        did = self.info.id
        for index in range(len(uv)):
            if self._stop.is_set():
                return
            target = start + index * period
            while True:
                delay = target - time.perf_counter()
                if delay <= 0:
                    break
                if self._stop.is_set():
                    return
                time.sleep(delay if delay < 0.02 else 0.02)
            handler(did, [float(x) for x in uv[index]])

    def _put_block(self, blocks: queue.Queue, block) -> None:
        while not self._stop.is_set():
            try:
                blocks.put(block, timeout=0.2)
                return
            except queue.Full:
                continue

    def _capture_loop(self, dev: ADS1299, blocks: queue.Queue) -> None:
        try:
            started = time.perf_counter()
            for block in iter_blocks(
                dev,
                chunk_frames=LIVE_CHUNK_FRAMES,
                stop_event=self._stop,
                gain=self._gain,
                gain_of=lambda: self._gain,
                as_microvolts=True,
                inter_block_pause_s=0.0,
            ):
                if self._stop.is_set():
                    break
                self._last_acquire_s = time.perf_counter() - started
                block.capture_gain = float(self._gain)
                self._put_block(blocks, block)
                started = time.perf_counter()
                pending, gen = self._take_pending()
                if pending is not None:
                    self._apply_frontend(dev, pending, gen)
        except Exception as exc:
            self._capture_error = exc
        finally:
            self._put_block(blocks, None)

    def _read_gain(self, dev: ADS1299) -> float:
        try:
            ch1 = dev.read_register("ch1set")
        except Exception:
            return 24.0
        return float(_GAIN_FROM_BITS.get((ch1 >> 4) & 7, 24))

    def _run(self) -> None:
        firmware = (self.info.meta or {}).get("firmware") or _firmware_hint() or None
        try:
            self._status(f"opening {self.info.name}")
            dev = ADS1299.open(load_fw=True, firmware=firmware)
            self._dev = dev
            dev.ensure_capture_defaults()
            try:
                self._sample_rate = int(round(dev.sample_rate_sps()))
            except Exception:
                pass
            try:
                version = dev.read_path("/version").strip()
            except Exception:
                version = ""
            cfg, gen = self._take_pending()
            if cfg is None:
                cfg = config_from_meta(self.info.meta)
            if cfg is not None:
                self._apply_frontend(dev, cfg, gen)
            else:
                self._gain = self._read_gain(dev)
                self._detail = version or "USBStyx"
            self._connected = True
            self._capture_error = None
            self._status(
                self._detail
                or f"streaming {self._sample_rate} SPS × {self.n_channels} ch"
            )
            blocks: queue.Queue = queue.Queue(maxsize=1)
            capture = threading.Thread(
                target=self._capture_loop,
                args=(dev, blocks),
                daemon=True,
                name=f"ads1299-cap-{self.info.id}",
            )
            capture.start()
            while not self._stop.is_set():
                try:
                    block = blocks.get(timeout=0.2)
                except queue.Empty:
                    continue
                if block is None:
                    break
                self._emit_paced(block)
            if self._capture_error is not None and not self._stop.is_set():
                text = str(self._capture_error).strip() or self._capture_error.__class__.__name__
                self._status(text, warn=True)
            capture.join(timeout=2.0)
        except Exception as exc:
            text = str(exc).strip() or exc.__class__.__name__
            self._status(text, warn=True)
        finally:
            self._connected = False
            dev = self._dev
            self._dev = None
            if dev is not None:
                try:
                    dev.close()
                except Exception:
                    pass
