# 7Being · ADS1299

English · [中文](#中文)

## English

Board plugin for [7Being](https://github.com/rush0100/7Being) — **TI ADS1299EEG-FE** on **MMB0**, a plugin for `sevenbeing`.

Talks to stock DSP firmware over **USBStyx** (9P on USB bulk). The evaluation GUI from the standalone client is not included — stream through sevenbeing / 7Being Studio instead.

Python import module: `sevenbeing_ads1299`. MIT licensed (`LICENSE`, and `native/LICENSE` for the Rust crate).

> **Not affiliated with Texas Instruments.** This package does **not** ship TI firmware. Obtain `ads1299evm-pdk.bin` from the [ADS1299EEGFE-PDK](https://www.ti.com/tool/ADS1299EEGFE-PDK) and point `ADS1299_FIRMWARE` at it.

The host library is adapted from [ads1299-mmb0](https://github.com/rush0100/ads1299-mmb0) (MIT). `ADS1299.open`, `acquire`, and the load/capture/shell CLI do not import `sevenbeing`.

### Install

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

The sevenbeing plugin (gRPC on port 51053) is optional:

```bash
pip install -e ".[sevenbeing]"
7being-ads1299-serve --port 51053
```

```python
from sevenbeing import CORE
CORE.devices.attach_grpc("127.0.0.1:51053")
found = CORE.devices.scan()
```

### USB IDs

| State | VID | PID |
|-------|-----|-----|
| Bootloader (before FW) | `0x0451` | `0x9001` |
| USBStyx (after FW) | `0x0451` | `0x5718` |

`scan()` lists whichever of those is on the bus. `connect()` loads firmware when the board is still in the bootloader, then streams **CH1–CH8** in microvolts.

Stock firmware fills an onboard buffer and then transfers USB (~1 MB). The driver emits those blocks back to back. Gaps between blocks are expected.

### Low-level API

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

## 中文

[7Being](https://github.com/rush0100/7Being) 的板卡插件 — **MMB0** 上的 **TI ADS1299EEG-FE**，作为 `sevenbeing` 的插件。

通过 **USBStyx**（USB bulk 上的 9P）与原厂 DSP 固件通信。不包含独立客户端的评估 GUI — 请经由 sevenbeing / 7Being Studio 取流。

Python 导入模块：`sevenbeing_ads1299`。MIT 许可（`LICENSE`；Rust crate 见 `native/LICENSE`）。

> **与 Texas Instruments 无隶属关系。** 本包**不附带** TI 固件。请从 [ADS1299EEGFE-PDK](https://www.ti.com/tool/ADS1299EEGFE-PDK) 取得 `ads1299evm-pdk.bin`，并用 `ADS1299_FIRMWARE` 指向该文件。

主机库改自 [ads1299-mmb0](https://github.com/rush0100/ads1299-mmb0)（MIT）。`ADS1299.open`、`acquire` 以及 load/capture/shell CLI 不导入 `sevenbeing`。

### 安装

```bash
# macOS USB bulk
brew install libusb

pip install -e .

# 可选：Rust 解码（每块一个微伏缓冲；跳过则回退到 NumPy）
pip install maturin
( cd native && maturin develop --release )
```

```bash
export ADS1299_FIRMWARE=/path/to/ads1299evm-pdk.bin
7being-ads1299-load --wait -f "$ADS1299_FIRMWARE"
```

sevenbeing 插件（gRPC，端口 51053）是可选的：

```bash
pip install -e ".[sevenbeing]"
7being-ads1299-serve --port 51053
```

```python
from sevenbeing import CORE
CORE.devices.attach_grpc("127.0.0.1:51053")
found = CORE.devices.scan()
```

### USB ID

| 状态 | VID | PID |
|------|-----|-----|
| Bootloader（固件之前） | `0x0451` | `0x9001` |
| USBStyx（固件之后） | `0x0451` | `0x5718` |

`scan()` 列出总线上的上述设备。板卡仍在 bootloader 时，`connect()` 会加载固件，然后以微伏流式输出 **CH1–CH8**。

原厂固件先填满板载缓冲，再做 USB 传输（约 1 MB）。驱动会连续送出这些块。块与块之间的间隔是预期行为。

### 底层 API

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

若采集失败后 USB bulk 卡住：给 MMB0 重新上电，等到 `0451:9001`，再加载一次。
