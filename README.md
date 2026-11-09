# 7Being · ADS1299

บอร์ดของ [7Being](https://github.com/rush0100/7Being) — **TI ADS1299EEG-FE** บน **MMB0** เป็นปลั๊กอินของ `sevenbeing`.

Talks to stock DSP firmware over **USBStyx** (9P on USB bulk). The evaluation GUI from the standalone client is not included — stream through sevenbeing / 7Being Studio instead.

Python import module: `sevenbeing_ads1299`. MIT licensed (`LICENSE`, and `native/LICENSE` for the Rust crate).

> **Not affiliated with Texas Instruments.** This package does **not** ship TI firmware. Obtain `ads1299evm-pdk.bin` from the [ADS1299EEGFE-PDK](https://www.ti.com/tool/ADS1299EEGFE-PDK) and point `ADS1299_FIRMWARE` at it.

Host library is adapted from [ads1299-mmb0](https://github.com/rush0100/ads1299-mmb0) (MIT). `ADS1299.open`, `acquire`, and the load/capture/shell CLI do not import `sevenbeing`.

## Install

```bash
# macOS USB bulk
brew install libusb

pip install -e .

# optional: Rust decode (one microvolt buffer per block; NumPy fallback if skipped)
pip install maturin
( cd native && maturin develop --release )
```

```bash
export ADS1299_FIRMWARE=/path/to/ads1299evm-pdk.bin
7being-ads1299-load --wait -f "$ADS1299_FIRMWARE"
```

sevenbeing plugin (gRPC on port 51053) is optional:

```bash
pip install -e ".[sevenbeing]"
7being-ads1299-serve --port 51053
```

```python
from sevenbeing import CORE
CORE.devices.attach_grpc("127.0.0.1:51053")
found = CORE.devices.scan()
```

## USB IDs

| State | VID | PID |
|-------|-----|-----|
| Bootloader (before FW) | `0x0451` | `0x9001` |
| USBStyx (after FW) | `0x0451` | `0x5718` |

`scan()` lists whichever of those is on the bus. `connect()` loads firmware when the board is still in the bootloader, then streams **CH1–CH8** in microvolts.

Stock firmware fills an onboard buffer and then transfers USB (~1 MB). The driver emits those blocks back to back. Gaps between blocks are expected.

## Low-level API

```python
from sevenbeing_ads1299 import ADS1299
from sevenbeing_ads1299.stream import acquire_continuous

with ADS1299.open() as dev:
    print(dev.read_path("/version"))
    volts = dev.acquire(n_samples=64)  # (64, 8) float volts
```

```bash
7being-ads1299-load --wait -f "$ADS1299_FIRMWARE"
7being-ads1299-capture -n 64 --npy out.npy
```

If USB bulk wedges after a failed acquire: power-cycle the MMB0 supply, wait for `0451:9001`, then load again.
